"""JIRA API service for ticket management and project tracking."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from jira import JIRA, JIRAError
from jira.resources import Issue, Sprint, Project

from ..config import settings
from ..models.core import JiraTicket


logger = logging.getLogger(__name__)


@dataclass
class JiraConnectionInfo:
    """Information about JIRA connection and server."""

    server_url: str
    username: str
    authenticated: bool
    server_info: Dict[str, Any]


class JiraAPIError(Exception):
    """Custom exception for JIRA API errors."""

    def __init__(
        self, message: str, status_code: Optional[int] = None, retry_after: Optional[int] = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class JiraService:
    """Service for interacting with JIRA API."""

    def __init__(
        self,
        server_url: Optional[str] = None,
        username: Optional[str] = None,
        token: Optional[str] = None,
    ):
        """Initialize JIRA service with authentication credentials."""
        self.server_url = server_url or settings.jira_url
        self.username = username or settings.jira_username
        self.token = token or settings.jira_token
        self._jira_client = None

        if not all([self.server_url, self.username, self.token]):
            logger.warning(
                "JIRA credentials not fully configured. " "Some functionality may not be available."
            )

    @property
    def jira_client(self) -> JIRA:
        """Lazy initialization of JIRA client."""
        if self._jira_client is None:
            if not all([self.server_url, self.username, self.token]):
                raise JiraAPIError(
                    "JIRA credentials not configured. Please set JIRA_URL, "
                    "JIRA_USERNAME, and JIRA_TOKEN environment variables."
                )

            try:
                self._jira_client = JIRA(
                    server=self.server_url,
                    basic_auth=(self.username, self.token),
                    options={"verify": True},
                )
                logger.info(f"Connected to JIRA server: {self.server_url}")
            except JIRAError as e:
                logger.error(f"Failed to connect to JIRA: {e}")
                raise JiraAPIError(f"JIRA connection failed: {e}")
            except Exception as e:
                logger.error(f"Unexpected error connecting to JIRA: {e}")
                raise JiraAPIError(f"Unexpected JIRA connection error: {e}")

        return self._jira_client

    async def _execute_with_retry(self, func, *args, max_retries: int = 3, **kwargs) -> Any:
        """Execute JIRA API call with retry logic and error handling."""
        last_exception = None

        for attempt in range(max_retries):
            try:
                # Execute the function
                result = func(*args, **kwargs)
                return result

            except JIRAError as e:
                logger.error(f"JIRA API error on attempt {attempt + 1}/{max_retries}: {e}")

                # Don't retry on authentication or permission errors
                if e.status_code in [401, 403]:
                    raise JiraAPIError(
                        f"JIRA authentication/permission error: {e}", status_code=e.status_code
                    )

                # Don't retry on not found errors
                if e.status_code == 404:
                    raise JiraAPIError(f"JIRA resource not found: {e}", status_code=e.status_code)

                if attempt == max_retries - 1:
                    raise JiraAPIError(
                        f"JIRA API error after retries: {e}", status_code=e.status_code
                    )

                # Exponential backoff for retryable errors
                await asyncio.sleep(2**attempt)
                last_exception = e

            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt == max_retries - 1:
                    raise JiraAPIError(f"Unexpected error: {e}")

                await asyncio.sleep(2**attempt)
                last_exception = e

        # This should never be reached, but just in case
        if last_exception:
            raise JiraAPIError(f"Failed after {max_retries} attempts: {last_exception}")

    async def test_authentication(self) -> JiraConnectionInfo:
        """Test JIRA authentication and return connection info."""
        try:
            client = self.jira_client

            # Get server info to verify connection
            server_info = await self._execute_with_retry(client.server_info)

            # Get current user info
            current_user = await self._execute_with_retry(client.current_user)

            return JiraConnectionInfo(
                server_url=self.server_url,
                username=current_user,
                authenticated=True,
                server_info={
                    "version": server_info.get("version", "Unknown"),
                    "build_number": server_info.get("buildNumber", "Unknown"),
                    "server_title": server_info.get("serverTitle", "Unknown"),
                },
            )

        except JiraAPIError:
            raise
        except Exception as e:
            raise JiraAPIError(f"Authentication test failed: {e}")

    def _convert_jira_issue_to_model(self, issue: Issue) -> JiraTicket:
        """Convert JIRA Issue object to our JiraTicket model."""
        try:
            # Calculate time in current status
            status_changed = None
            if hasattr(issue, "changelog") and issue.changelog:
                # Find the most recent status change
                for history in reversed(issue.changelog.histories):
                    for item in history.items:
                        if item.field == "status":
                            status_changed = datetime.strptime(
                                history.created[:19], "%Y-%m-%dT%H:%M:%S"
                            )
                            break
                    if status_changed:
                        break

            # If no status change found, use created date
            if not status_changed:
                status_changed = datetime.strptime(issue.fields.created[:19], "%Y-%m-%dT%H:%M:%S")

            time_in_status = datetime.now() - status_changed

            # Determine if ticket is blocked
            blocked = False
            if hasattr(issue.fields, "labels") and issue.fields.labels:
                blocked = any("blocked" in str(label).lower() for label in issue.fields.labels)

            # Check for blocker in status or priority
            if not blocked:
                status_lower = str(issue.fields.status.name).lower()
                blocked = "blocked" in status_lower or "impediment" in status_lower

            # Extract sprint name safely
            sprint_name = self._extract_sprint_name(issue)

            return JiraTicket(
                key=str(issue.key),
                summary=str(issue.fields.summary),
                status=str(issue.fields.status.name),
                assignee=str(issue.fields.assignee.displayName) if issue.fields.assignee else None,
                priority=str(issue.fields.priority.name) if issue.fields.priority else "None",
                story_points=getattr(issue.fields, "customfield_10016", None),
                sprint=sprint_name,
                blocked=blocked,
                last_updated=datetime.strptime(issue.fields.updated[:19], "%Y-%m-%dT%H:%M:%S"),
                time_in_status=time_in_status,
            )

        except Exception as e:
            logger.error(f"Failed to convert JIRA issue {issue.key}: {e}")
            # Return a minimal ticket if conversion fails
            return JiraTicket(
                key=str(issue.key),
                summary=str(getattr(issue.fields, "summary", "Unknown")),
                status=str(getattr(issue.fields.status, "name", "Unknown")),
                assignee=None,
                priority="None",
                story_points=None,
                sprint=None,
                blocked=False,
                last_updated=datetime.now(),
                time_in_status=timedelta(0),
            )

    def _extract_sprint_name(self, issue: Issue) -> Optional[str]:
        """Extract sprint name from JIRA issue."""
        try:
            # Try common sprint field names
            sprint_fields = ["customfield_10020", "customfield_10010", "sprint"]

            for field_name in sprint_fields:
                sprint_data = getattr(issue.fields, field_name, None)
                if sprint_data:
                    if isinstance(sprint_data, list) and sprint_data:
                        # Take the last (most recent) sprint
                        sprint_obj = sprint_data[-1]
                        if hasattr(sprint_obj, "name"):
                            return str(sprint_obj.name)
                        elif isinstance(sprint_obj, str):
                            # Parse sprint string format
                            import re

                            match = re.search(r"name=([^,\]]+)", sprint_obj)
                            if match:
                                return match.group(1)
                    elif hasattr(sprint_data, "name"):
                        return str(sprint_data.name)

            return None

        except Exception as e:
            logger.debug(f"Could not extract sprint from issue {issue.key}: {e}")
            return None

    async def get_projects(self) -> List[Dict[str, Any]]:
        """Get list of available JIRA projects."""
        try:
            projects = await self._execute_with_retry(self.jira_client.projects)

            project_list = []
            for project in projects:
                project_list.append(
                    {
                        "key": project.key,
                        "name": project.name,
                        "id": project.id,
                        "project_type": getattr(project, "projectTypeKey", "Unknown"),
                    }
                )

            logger.info(f"Retrieved {len(project_list)} JIRA projects")
            return project_list

        except JiraAPIError:
            raise
        except Exception as e:
            raise JiraAPIError(f"Failed to get JIRA projects: {e}")

    async def get_issues_by_jql(
        self, jql_query: str, max_results: int = 100, expand: str = "changelog"
    ) -> List[JiraTicket]:
        """Get issues using JQL (JIRA Query Language)."""
        try:
            issues = await self._execute_with_retry(
                self.jira_client.search_issues, jql_query, maxResults=max_results, expand=expand
            )

            tickets = []
            for issue in issues:
                try:
                    ticket = self._convert_jira_issue_to_model(issue)
                    tickets.append(ticket)
                except Exception as e:
                    logger.error(f"Failed to convert issue {issue.key}: {e}")
                    continue

            logger.info(f"Retrieved {len(tickets)} tickets using JQL: {jql_query}")
            return tickets

        except JiraAPIError:
            raise
        except Exception as e:
            raise JiraAPIError(f"Failed to execute JQL query '{jql_query}': {e}")

    async def get_active_tickets(
        self, project_key: Optional[str] = None, assignee: Optional[str] = None
    ) -> List[JiraTicket]:
        """Get active (non-closed) tickets."""
        try:
            # Build JQL query
            jql_parts = ['status != "Done"', 'status != "Closed"', 'status != "Resolved"']

            if project_key:
                jql_parts.append(f'project = "{project_key}"')

            if assignee:
                if assignee.lower() == "currentuser":
                    jql_parts.append("assignee = currentUser()")
                else:
                    jql_parts.append(f'assignee = "{assignee}"')

            jql_query = " AND ".join(jql_parts)
            jql_query += " ORDER BY updated DESC"

            return await self.get_issues_by_jql(jql_query)

        except JiraAPIError:
            raise
        except Exception as e:
            raise JiraAPIError(f"Failed to get active tickets: {e}")

    async def get_tickets_in_sprint(self, sprint_id: int) -> List[JiraTicket]:
        """Get all tickets in a specific sprint."""
        try:
            jql_query = f"sprint = {sprint_id} ORDER BY rank ASC"
            return await self.get_issues_by_jql(jql_query)

        except JiraAPIError:
            raise
        except Exception as e:
            raise JiraAPIError(f"Failed to get tickets for sprint {sprint_id}: {e}")

    async def get_current_sprint_tickets(self, board_id: int) -> List[JiraTicket]:
        """Get tickets in the current active sprint for a board."""
        try:
            # Get active sprints for the board
            sprints = await self._execute_with_retry(
                self.jira_client.sprints, board_id, state="active"
            )

            if not sprints:
                logger.info(f"No active sprints found for board {board_id}")
                return []

            # Get tickets from the first active sprint
            active_sprint = sprints[0]
            return await self.get_tickets_in_sprint(active_sprint.id)

        except JiraAPIError:
            raise
        except Exception as e:
            raise JiraAPIError(f"Failed to get current sprint tickets: {e}")

    async def detect_blocked_tickets(
        self, tickets: Optional[List[JiraTicket]] = None, stale_days: int = 7
    ) -> List[Dict[str, Any]]:
        """Detect potentially blocked or stale tickets."""
        try:
            if tickets is None:
                tickets = await self.get_active_tickets()

            blocked_tickets = []
            now = datetime.now()

            for ticket in tickets:
                blocker_reasons = []
                severity = "low"

                # Check if explicitly marked as blocked
                if ticket.blocked:
                    blocker_reasons.append("Explicitly marked as blocked")
                    severity = "high"

                # Check if ticket has been in same status too long
                if ticket.time_in_status.days >= stale_days:
                    blocker_reasons.append(
                        f"In '{ticket.status}' status for {ticket.time_in_status.days} days"
                    )
                    if ticket.time_in_status.days >= stale_days * 2:
                        severity = "high"
                    elif severity == "low":
                        severity = "medium"

                # Check if ticket hasn't been updated recently
                days_since_update = (now - ticket.last_updated).days
                if days_since_update >= stale_days:
                    blocker_reasons.append(f"No updates for {days_since_update} days")
                    if days_since_update >= stale_days * 2:
                        severity = "high"
                    elif severity == "low":
                        severity = "medium"

                # Check for specific blocking statuses
                blocking_statuses = [
                    "blocked",
                    "impediment",
                    "waiting",
                    "on hold",
                    "pending",
                    "suspended",
                ]
                if any(status in ticket.status.lower() for status in blocking_statuses):
                    blocker_reasons.append(f"Status indicates blocking: {ticket.status}")
                    severity = "high"

                # If any blocker reasons found, add to list
                if blocker_reasons:
                    blocked_tickets.append(
                        {
                            "ticket": ticket,
                            "reasons": blocker_reasons,
                            "severity": severity,
                            "days_in_status": ticket.time_in_status.days,
                            "days_since_update": days_since_update,
                        }
                    )

            # Sort by severity and days in status
            severity_order = {"high": 3, "medium": 2, "low": 1}
            blocked_tickets.sort(
                key=lambda x: (severity_order[x["severity"]], x["days_in_status"]), reverse=True
            )

            logger.info(f"Detected {len(blocked_tickets)} potentially blocked tickets")
            return blocked_tickets

        except JiraAPIError:
            raise
        except Exception as e:
            raise JiraAPIError(f"Failed to detect blocked tickets: {e}")

    async def get_ticket_details(self, ticket_key: str) -> Optional[JiraTicket]:
        """Get detailed information about a specific ticket."""
        try:
            issue = await self._execute_with_retry(
                self.jira_client.issue, ticket_key, expand="changelog"
            )

            return self._convert_jira_issue_to_model(issue)

        except JiraAPIError as e:
            if e.status_code == 404:
                logger.warning(f"Ticket {ticket_key} not found")
                return None
            raise
        except Exception as e:
            raise JiraAPIError(f"Failed to get ticket {ticket_key} details: {e}")

    async def sync_tickets(
        self, project_key: Optional[str] = None, updated_since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Sync ticket data from JIRA and return summary."""
        try:
            # Build JQL for tickets to sync
            jql_parts = []

            if project_key:
                jql_parts.append(f'project = "{project_key}"')

            if updated_since:
                updated_str = updated_since.strftime("%Y-%m-%d %H:%M")
                jql_parts.append(f'updated >= "{updated_str}"')
            else:
                # Default to last 24 hours if no date specified
                yesterday = datetime.now() - timedelta(days=1)
                updated_str = yesterday.strftime("%Y-%m-%d %H:%M")
                jql_parts.append(f'updated >= "{updated_str}"')

            jql_query = " AND ".join(jql_parts) if jql_parts else "updated >= -24h"
            jql_query += " ORDER BY updated DESC"

            # Get updated tickets
            tickets = await self.get_issues_by_jql(jql_query, max_results=500)

            # Detect blockers in the synced tickets
            blocked_tickets = await self.detect_blocked_tickets(tickets)

            # Generate summary
            summary = {
                "sync_timestamp": datetime.now().isoformat(),
                "total_tickets_synced": len(tickets),
                "blocked_tickets_detected": len(blocked_tickets),
                "tickets_by_status": {},
                "tickets_by_assignee": {},
                "blocked_tickets": [],
            }

            # Analyze synced tickets
            for ticket in tickets:
                # Count by status
                if ticket.status not in summary["tickets_by_status"]:
                    summary["tickets_by_status"][ticket.status] = 0
                summary["tickets_by_status"][ticket.status] += 1

                # Count by assignee
                assignee = ticket.assignee or "Unassigned"
                if assignee not in summary["tickets_by_assignee"]:
                    summary["tickets_by_assignee"][assignee] = 0
                summary["tickets_by_assignee"][assignee] += 1

            # Add blocked ticket details
            for blocked in blocked_tickets:
                ticket = blocked["ticket"]
                summary["blocked_tickets"].append(
                    {
                        "key": ticket.key,
                        "summary": ticket.summary,
                        "status": ticket.status,
                        "assignee": ticket.assignee,
                        "severity": blocked["severity"],
                        "reasons": blocked["reasons"],
                        "days_in_status": blocked["days_in_status"],
                    }
                )

            logger.info(f"Synced {len(tickets)} tickets, detected {len(blocked_tickets)} blockers")
            return summary

        except JiraAPIError:
            raise
        except Exception as e:
            raise JiraAPIError(f"Failed to sync tickets: {e}")

    async def store_tickets_in_database(self, tickets: List[JiraTicket]) -> Dict[str, Any]:
        """Store or update JIRA tickets in the database."""
        try:
            from ..database.connection import get_database

            db = await get_database()
            stored_count = 0
            updated_count = 0
            errors = []

            for ticket in tickets:
                try:
                    # Prepare ticket data for database
                    ticket_data = {
                        "key": ticket.key,
                        "summary": ticket.summary,
                        "status": ticket.status,
                        "assignee": ticket.assignee,
                        "priority": ticket.priority,
                        "story_points": ticket.story_points,
                        "sprint": ticket.sprint,
                        "blocked": ticket.blocked,
                        "last_updated": ticket.last_updated.isoformat(),
                        "data": {
                            "time_in_status_days": ticket.time_in_status.days,
                            "time_in_status_seconds": ticket.time_in_status.total_seconds(),
                        },
                    }

                    # Check if ticket already exists
                    existing = await db.select(
                        table="jira_tickets",
                        filters={"key": ticket.key},
                        select_fields="key",
                    )

                    if existing:
                        # Update existing ticket
                        result = await db.update(
                            table="jira_tickets",
                            data=ticket_data,
                            filters={"key": ticket.key},
                        )
                        updated_count += 1
                    else:
                        # Insert new ticket
                        result = await db.insert(table="jira_tickets", data=ticket_data)
                        stored_count += 1

                except Exception as e:
                    errors.append(f"Error processing {ticket.key}: {str(e)}")
                    logger.error(f"Error storing ticket {ticket.key}: {e}")

            summary = {
                "total_processed": len(tickets),
                "stored_count": stored_count,
                "updated_count": updated_count,
                "error_count": len(errors),
                "errors": errors,
            }

            logger.info(
                f"Database storage complete: {stored_count} stored, "
                f"{updated_count} updated, {len(errors)} errors"
            )
            return summary

        except Exception as e:
            logger.error(f"Failed to store tickets in database: {e}")
            raise JiraAPIError(f"Database storage failed: {e}")

    async def store_blocked_tickets(self, blocked_tickets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store detected blocked tickets in the bottlenecks table."""
        try:
            from ..database.connection import get_database

            db = await get_database()
            stored_count = 0
            errors = []

            for blocked in blocked_tickets:
                try:
                    ticket = blocked["ticket"]

                    # Prepare bottleneck data
                    bottleneck_data = {
                        "type": "ticket_blocked",
                        "severity": blocked["severity"],
                        "description": f"JIRA ticket {ticket.key} is blocked: {', '.join(blocked['reasons'])}",
                        "affected_items": [ticket.key],
                        "resolved": False,
                    }

                    # Check if this bottleneck already exists and is unresolved
                    existing = await db.select(
                        table="bottlenecks",
                        filters={"type": "ticket_blocked", "resolved": False},
                        select_fields="id, affected_items",
                    )

                    # Check if this ticket is already in an existing bottleneck
                    ticket_already_tracked = False
                    if existing["success"] and existing["data"]:
                        for bottleneck in existing["data"]:
                            if ticket.key in bottleneck.get("affected_items", []):
                                ticket_already_tracked = True
                                break

                    if not ticket_already_tracked:
                        result = await db.insert(table="bottlenecks", data=bottleneck_data)
                        if result["success"]:
                            stored_count += 1
                        else:
                            errors.append(
                                f"Failed to store bottleneck for {ticket.key}: {result['error']}"
                            )

                except Exception as e:
                    errors.append(f"Error processing blocked ticket: {str(e)}")
                    logger.error(f"Error storing blocked ticket: {e}")

            summary = {
                "total_processed": len(blocked_tickets),
                "stored_count": stored_count,
                "error_count": len(errors),
                "errors": errors,
            }

            logger.info(
                f"Blocked tickets storage complete: {stored_count} stored, {len(errors)} errors"
            )
            return summary

        except Exception as e:
            logger.error(f"Failed to store blocked tickets: {e}")
            raise JiraAPIError(f"Blocked tickets storage failed: {e}")

    async def sync_and_store_tickets(
        self, project_key: Optional[str] = None, updated_since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Sync tickets from JIRA and store them in database with blocker detection."""
        try:
            # Sync tickets from JIRA
            sync_summary = await self.sync_tickets(project_key, updated_since)

            # Get the actual ticket objects for database storage
            jql_parts = []

            if project_key:
                jql_parts.append(f'project = "{project_key}"')

            if updated_since:
                updated_str = updated_since.strftime("%Y-%m-%d %H:%M")
                jql_parts.append(f'updated >= "{updated_str}"')
            else:
                # Default to last 24 hours if no date specified
                yesterday = datetime.now() - timedelta(days=1)
                updated_str = yesterday.strftime("%Y-%m-%d %H:%M")
                jql_parts.append(f'updated >= "{updated_str}"')

            jql_query = " AND ".join(jql_parts) if jql_parts else "updated >= -24h"
            jql_query += " ORDER BY updated DESC"

            tickets = await self.get_issues_by_jql(jql_query, max_results=500)

            # Store tickets in database
            storage_summary = await self.store_tickets_in_database(tickets)

            # Detect and store blocked tickets
            blocked_tickets = await self.detect_blocked_tickets(tickets)
            blocked_storage_summary = await self.store_blocked_tickets(blocked_tickets)

            # Combine summaries
            combined_summary = {
                "sync_summary": sync_summary,
                "storage_summary": storage_summary,
                "blocked_storage_summary": blocked_storage_summary,
                "total_tickets_processed": len(tickets),
                "total_blocked_detected": len(blocked_tickets),
            }

            logger.info(
                f"Complete sync and storage: {len(tickets)} tickets processed, "
                f"{len(blocked_tickets)} blockers detected"
            )
            return combined_summary

        except JiraAPIError:
            raise
        except Exception as e:
            raise JiraAPIError(f"Sync and storage failed: {e}")

    async def get_tickets_from_database(
        self,
        project_key: Optional[str] = None,
        status_filter: Optional[str] = None,
        assignee_filter: Optional[str] = None,
        blocked_only: bool = False,
    ) -> List[JiraTicket]:
        """Retrieve tickets from database with optional filters."""
        try:
            from ..database.connection import get_database

            db = await get_database()
            filters = {}

            if project_key:
                # Note: This assumes project key is part of the ticket key (e.g., "PROJ-123")
                # You might need to adjust this based on your data structure
                pass  # We'll use a more complex query for this

            if status_filter:
                filters["status"] = status_filter

            if assignee_filter:
                filters["assignee"] = assignee_filter

            if blocked_only:
                filters["blocked"] = True

            result = await db.select(
                table="jira_tickets",
                filters=filters if filters else None,
                select_fields="*",
            )

            if not result["success"]:
                raise JiraAPIError(f"Failed to retrieve tickets from database: {result['error']}")

            tickets = []
            for row in result["data"] or []:
                try:
                    # Reconstruct time_in_status from stored data
                    time_in_status_days = row.get("data", {}).get("time_in_status_days", 0)
                    time_in_status = timedelta(days=time_in_status_days)

                    ticket = JiraTicket(
                        key=row["key"],
                        summary=row["summary"],
                        status=row["status"],
                        assignee=row["assignee"],
                        priority=row["priority"],
                        story_points=row["story_points"],
                        sprint=row["sprint"],
                        blocked=row["blocked"],
                        last_updated=datetime.fromisoformat(row["last_updated"]),
                        time_in_status=time_in_status,
                    )
                    tickets.append(ticket)
                except Exception as e:
                    logger.error(f"Error reconstructing ticket from database row: {e}")
                    continue

            logger.info(f"Retrieved {len(tickets)} tickets from database")
            return tickets

        except JiraAPIError:
            raise
        except Exception as e:
            raise JiraAPIError(f"Failed to retrieve tickets from database: {e}")

    async def resolve_bottleneck(self, bottleneck_id: str) -> bool:
        """Mark a bottleneck as resolved."""
        try:
            from ..database.connection import get_database

            db = await get_database()

            result = await db.update(
                table="bottlenecks",
                data={"resolved": True, "resolved_at": datetime.now().isoformat()},
                filters={"id": bottleneck_id},
            )

            if result["success"]:
                logger.info(f"Bottleneck {bottleneck_id} marked as resolved")
                return True
            else:
                logger.error(f"Failed to resolve bottleneck {bottleneck_id}: {result['error']}")
                return False

        except Exception as e:
            logger.error(f"Error resolving bottleneck {bottleneck_id}: {e}")
            return False

    async def create_ticket_from_pr(
        self,
        pr_title: str,
        pr_description: str,
        pr_author: str,
        pr_url: str,
        project_key: str,
        issue_type: str = "Task",
    ) -> Optional[str]:
        """Create a JIRA ticket from a GitHub PR."""
        try:
            # Prepare ticket data
            summary = f"Review PR: {pr_title}"
            description = f"""
GitHub Pull Request Review

**PR Title:** {pr_title}
**Author:** {pr_author}
**PR URL:** {pr_url}

**Description:**
{pr_description or 'No description provided'}

**Tasks:**
- [ ] Code review
- [ ] Testing
- [ ] Approval
            """.strip()

            issue_data = {
                "project": {"key": project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": issue_type},
                "labels": ["github-pr", "code-review"],
            }

            # Create the issue
            new_issue = await self._execute_with_retry(
                self.jira_client.create_issue, fields=issue_data
            )

            logger.info(f"Created JIRA ticket {new_issue.key} for PR: {pr_title}")
            return new_issue.key

        except JiraAPIError:
            raise
        except Exception as e:
            raise JiraAPIError(f"Failed to create JIRA ticket from PR: {e}")

    async def link_pr_to_ticket(self, ticket_key: str, pr_url: str, pr_title: str) -> bool:
        """Link a GitHub PR to an existing JIRA ticket."""
        try:
            # Add a comment with PR link
            comment_text = f"""
GitHub Pull Request linked to this ticket:

**PR:** [{pr_title}]({pr_url})
**Status:** Under Review
            """.strip()

            await self._execute_with_retry(self.jira_client.add_comment, ticket_key, comment_text)

            # Add GitHub PR label if not already present
            issue = await self._execute_with_retry(self.jira_client.issue, ticket_key)

            current_labels = (
                [label.name for label in issue.fields.labels] if issue.fields.labels else []
            )
            if "github-pr" not in current_labels:
                current_labels.append("github-pr")
                issue.update(labels=current_labels)

            logger.info(f"Linked PR {pr_url} to JIRA ticket {ticket_key}")
            return True

        except JiraAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to link PR to ticket {ticket_key}: {e}")
            return False

    async def update_ticket_from_pr_status(
        self, ticket_key: str, pr_status: str, pr_url: str, pr_merged: bool = False
    ) -> bool:
        """Update JIRA ticket status based on PR status."""
        try:
            issue = await self._execute_with_retry(self.jira_client.issue, ticket_key)

            current_status = issue.fields.status.name.lower()
            comment_text = ""
            new_status = None

            if pr_merged:
                # PR was merged - resolve the ticket
                if current_status not in ["done", "resolved", "closed"]:
                    new_status = "Done"  # or 'Resolved' depending on your workflow
                    comment_text = f"✅ **PR Merged:** [{pr_url}]({pr_url})\n\nCode has been successfully merged. Resolving ticket."

            elif pr_status == "closed":
                # PR was closed without merging
                if current_status not in ["done", "resolved", "closed"]:
                    new_status = "Closed"
                    comment_text = f"❌ **PR Closed:** [{pr_url}]({pr_url})\n\nPR was closed without merging. Closing ticket."

            elif pr_status == "approved":
                # PR was approved - move to ready for merge or similar
                if current_status in ["to do", "in progress", "in review"]:
                    new_status = "Ready for Merge"  # Adjust based on your workflow
                    comment_text = f"✅ **PR Approved:** [{pr_url}]({pr_url})\n\nPR has been approved and is ready for merge."

            elif pr_status == "changes_requested":
                # Changes requested - move back to in progress
                if current_status not in ["in progress"]:
                    new_status = "In Progress"
                    comment_text = f"🔄 **Changes Requested:** [{pr_url}]({pr_url})\n\nReviewer requested changes. Moving back to In Progress."

            elif pr_status == "review_requested":
                # PR is ready for review
                if current_status in ["to do", "in progress"]:
                    new_status = "In Review"
                    comment_text = (
                        f"👀 **Review Requested:** [{pr_url}]({pr_url})\n\nPR is ready for review."
                    )

            # Add comment about status change
            if comment_text:
                await self._execute_with_retry(
                    self.jira_client.add_comment, ticket_key, comment_text
                )

            # Update status if needed
            if new_status:
                try:
                    # Get available transitions
                    transitions = await self._execute_with_retry(
                        self.jira_client.transitions, issue
                    )

                    # Find the transition to the desired status
                    transition_id = None
                    for transition in transitions:
                        if transition["to"]["name"].lower() == new_status.lower():
                            transition_id = transition["id"]
                            break

                    if transition_id:
                        await self._execute_with_retry(
                            self.jira_client.transition_issue, issue, transition_id
                        )
                        logger.info(f"Updated JIRA ticket {ticket_key} status to {new_status}")
                    else:
                        logger.warning(
                            f"No transition found to status '{new_status}' for ticket {ticket_key}"
                        )

                except Exception as e:
                    logger.error(f"Failed to transition ticket {ticket_key} to {new_status}: {e}")
                    # Continue execution even if transition fails

            return True

        except JiraAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to update ticket {ticket_key} from PR status: {e}")
            return False

    async def find_ticket_for_pr(
        self, pr_title: str, pr_author: str, project_key: Optional[str] = None
    ) -> Optional[str]:
        """Find existing JIRA ticket that might be related to a PR."""
        try:
            # Search for tickets with similar summary or created by the same author
            jql_parts = []

            if project_key:
                jql_parts.append(f'project = "{project_key}"')

            # Look for tickets with similar title or by same author
            jql_parts.append('status != "Done" AND status != "Resolved" AND status != "Closed"')

            # Search by author first (assuming JIRA username matches GitHub username)
            author_jql = " AND ".join(jql_parts + [f'assignee = "{pr_author}"'])

            tickets = await self.get_issues_by_jql(author_jql, max_results=10)

            # Look for tickets with similar titles
            pr_title_lower = pr_title.lower()
            for ticket in tickets:
                ticket_summary_lower = ticket.summary.lower()

                # Simple similarity check - you could use more sophisticated matching
                if any(
                    word in ticket_summary_lower for word in pr_title_lower.split() if len(word) > 3
                ) or any(
                    word in pr_title_lower for word in ticket_summary_lower.split() if len(word) > 3
                ):
                    logger.info(f"Found potentially related ticket {ticket.key} for PR: {pr_title}")
                    return ticket.key

            return None

        except Exception as e:
            logger.error(f"Error finding ticket for PR '{pr_title}': {e}")
            return None

    async def handle_github_pr_event(
        self, event_type: str, pr_data: Dict[str, Any], project_key: str
    ) -> Dict[str, Any]:
        """Handle GitHub PR webhook events and sync with JIRA."""
        try:
            pr_title = pr_data.get("title", "")
            pr_author = pr_data.get("user", {}).get("login", "")
            pr_url = pr_data.get("html_url", "")
            pr_description = pr_data.get("body", "")
            pr_state = pr_data.get("state", "")
            pr_merged = pr_data.get("merged", False)

            result = {
                "event_type": event_type,
                "pr_title": pr_title,
                "pr_author": pr_author,
                "action_taken": None,
                "ticket_key": None,
                "success": False,
                "error": None,
            }

            if event_type == "opened":
                # PR was opened - create ticket or link to existing
                existing_ticket = await self.find_ticket_for_pr(pr_title, pr_author, project_key)

                if existing_ticket:
                    # Link to existing ticket
                    success = await self.link_pr_to_ticket(existing_ticket, pr_url, pr_title)
                    if success:
                        await self.update_ticket_from_pr_status(
                            existing_ticket, "review_requested", pr_url
                        )
                        result.update(
                            {
                                "action_taken": "linked_to_existing",
                                "ticket_key": existing_ticket,
                                "success": True,
                            }
                        )
                    else:
                        result["error"] = "Failed to link to existing ticket"
                else:
                    # Create new ticket
                    ticket_key = await self.create_ticket_from_pr(
                        pr_title, pr_description, pr_author, pr_url, project_key
                    )
                    if ticket_key:
                        result.update(
                            {
                                "action_taken": "created_new_ticket",
                                "ticket_key": ticket_key,
                                "success": True,
                            }
                        )
                    else:
                        result["error"] = "Failed to create new ticket"

            elif event_type in ["closed", "merged"]:
                # Find associated ticket and update status
                # You might want to store PR-ticket mappings in database for better tracking
                existing_ticket = await self.find_ticket_for_pr(pr_title, pr_author, project_key)

                if existing_ticket:
                    success = await self.update_ticket_from_pr_status(
                        existing_ticket, "merged" if pr_merged else "closed", pr_url, pr_merged
                    )
                    if success:
                        result.update(
                            {
                                "action_taken": "updated_status",
                                "ticket_key": existing_ticket,
                                "success": True,
                            }
                        )
                    else:
                        result["error"] = "Failed to update ticket status"
                else:
                    result["error"] = "No associated ticket found"

            elif event_type == "review_submitted":
                # Handle PR review events
                review_state = pr_data.get("review", {}).get("state", "")
                existing_ticket = await self.find_ticket_for_pr(pr_title, pr_author, project_key)

                if existing_ticket:
                    success = await self.update_ticket_from_pr_status(
                        existing_ticket, review_state, pr_url
                    )
                    if success:
                        result.update(
                            {
                                "action_taken": "updated_from_review",
                                "ticket_key": existing_ticket,
                                "success": True,
                            }
                        )
                    else:
                        result["error"] = "Failed to update from review"
                else:
                    result["error"] = "No associated ticket found"

            logger.info(
                f"Handled GitHub PR event: {event_type} for {pr_title} - {result['action_taken']}"
            )
            return result

        except Exception as e:
            logger.error(f"Error handling GitHub PR event {event_type}: {e}")
            return {"event_type": event_type, "success": False, "error": str(e)}

    # GitHub to JIRA Integration Methods

    async def create_ticket_from_pr(
        self, pr_data: Dict[str, Any], project_key: str, issue_type: str = "Task"
    ) -> Optional[str]:
        """Create a JIRA ticket from a GitHub PR."""
        try:
            # Extract PR information
            pr_number = pr_data.get("number")
            pr_title = pr_data.get("title", "Unknown PR")
            pr_body = pr_data.get("body", "")
            pr_author = pr_data.get("user", {}).get("login", "Unknown")
            pr_url = pr_data.get("html_url", "")

            # Create ticket summary and description
            summary = f"PR #{pr_number}: {pr_title}"
            description = f"""
GitHub Pull Request: {pr_url}
Author: {pr_author}

{pr_body}

---
This ticket was automatically created from GitHub PR #{pr_number}.
            """.strip()

            # Prepare issue data
            issue_data = {
                "project": {"key": project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": issue_type},
                "labels": ["github-pr", f"pr-{pr_number}"],
            }

            # Create the issue
            new_issue = await self._execute_with_retry(
                self.jira_client.create_issue, fields=issue_data
            )

            ticket_key = new_issue.key
            logger.info(f"Created JIRA ticket {ticket_key} for PR #{pr_number}")

            # Store the PR-to-ticket mapping in database
            await self._store_pr_ticket_mapping(pr_number, ticket_key, pr_url)

            return ticket_key

        except JiraAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to create JIRA ticket from PR #{pr_number}: {e}")
            raise JiraAPIError(f"Failed to create ticket from PR: {e}")

    async def update_ticket_from_pr_status(self, pr_data: Dict[str, Any], action: str) -> bool:
        """Update JIRA ticket status based on PR state changes."""
        try:
            pr_number = pr_data.get("number")
            pr_state = pr_data.get("state", "open")
            pr_merged = pr_data.get("merged", False)

            # Find the associated JIRA ticket
            ticket_key = await self._get_ticket_for_pr(pr_number)
            if not ticket_key:
                logger.warning(f"No JIRA ticket found for PR #{pr_number}")
                return False

            # Determine the target status based on PR state and action
            target_status = None

            if action == "closed" and pr_merged:
                target_status = "Done"  # PR was merged
            elif action == "closed" and not pr_merged:
                target_status = "Cancelled"  # PR was closed without merging
            elif action == "reopened":
                target_status = "In Progress"  # PR was reopened
            elif action == "ready_for_review":
                target_status = "In Review"  # PR is ready for review

            if target_status:
                success = await self._transition_ticket_status(ticket_key, target_status)
                if success:
                    logger.info(
                        f"Updated JIRA ticket {ticket_key} to '{target_status}' for PR #{pr_number}"
                    )
                return success

            return True  # No status change needed

        except Exception as e:
            logger.error(f"Failed to update JIRA ticket for PR #{pr_number}: {e}")
            return False

    async def update_ticket_from_pr_review(
        self, pr_data: Dict[str, Any], review_data: Dict[str, Any]
    ) -> bool:
        """Update JIRA ticket based on PR review state."""
        try:
            pr_number = pr_data.get("number")
            review_state = review_data.get("state", "").lower()
            reviewer = review_data.get("user", {}).get("login", "Unknown")

            # Find the associated JIRA ticket
            ticket_key = await self._get_ticket_for_pr(pr_number)
            if not ticket_key:
                logger.warning(f"No JIRA ticket found for PR #{pr_number}")
                return False

            # Add a comment to the ticket about the review
            comment_text = f"GitHub PR Review by {reviewer}: {review_state.title()}"
            if review_data.get("body"):
                comment_text += f"\n\n{review_data['body']}"

            await self._add_comment_to_ticket(ticket_key, comment_text)

            # Update ticket status based on review state
            target_status = None
            if review_state == "approved":
                target_status = "Ready for Merge"
            elif review_state == "changes_requested":
                target_status = "Changes Requested"

            if target_status:
                success = await self._transition_ticket_status(ticket_key, target_status)
                if success:
                    logger.info(
                        f"Updated JIRA ticket {ticket_key} to '{target_status}' based on review"
                    )
                return success

            return True

        except Exception as e:
            logger.error(f"Failed to update JIRA ticket for PR review: {e}")
            return False

    async def _store_pr_ticket_mapping(self, pr_number: int, ticket_key: str, pr_url: str) -> None:
        """Store PR to JIRA ticket mapping in database."""
        try:
            from ..database.connection import get_database

            db = await get_database()

            mapping_data = {
                "pr_number": pr_number,
                "ticket_key": ticket_key,
                "pr_url": pr_url,
                "created_at": datetime.now().isoformat(),
            }

            result = await db.insert(table="pr_ticket_mappings", data=mapping_data)

            if not result["success"]:
                logger.error(f"Failed to store PR-ticket mapping: {result['error']}")

        except Exception as e:
            logger.error(f"Error storing PR-ticket mapping: {e}")

    async def _get_ticket_for_pr(self, pr_number: int) -> Optional[str]:
        """Get JIRA ticket key for a given PR number."""
        try:
            from ..database.connection import get_database

            db = await get_database()

            result = await db.select(
                table="pr_ticket_mappings",
                filters={"pr_number": pr_number},
                select_fields="ticket_key",
            )

            if result["success"] and result["data"]:
                return result["data"][0]["ticket_key"]

            return None

        except Exception as e:
            logger.error(f"Error getting ticket for PR #{pr_number}: {e}")
            return None

    async def _transition_ticket_status(self, ticket_key: str, target_status: str) -> bool:
        """Transition a JIRA ticket to a target status."""
        try:
            # Get the issue
            issue = await self._execute_with_retry(self.jira_client.issue, ticket_key)

            # Get available transitions
            transitions = await self._execute_with_retry(self.jira_client.transitions, issue)

            # Find the transition that leads to the target status
            target_transition = None
            for transition in transitions:
                if transition["to"]["name"].lower() == target_status.lower():
                    target_transition = transition
                    break

            if not target_transition:
                logger.warning(f"No transition found to '{target_status}' for ticket {ticket_key}")
                return False

            # Perform the transition
            await self._execute_with_retry(
                self.jira_client.transition_issue, issue, target_transition["id"]
            )

            logger.info(f"Transitioned ticket {ticket_key} to '{target_status}'")
            return True

        except Exception as e:
            logger.error(f"Failed to transition ticket {ticket_key} to '{target_status}': {e}")
            return False

    async def _add_comment_to_ticket(self, ticket_key: str, comment_text: str) -> bool:
        """Add a comment to a JIRA ticket."""
        try:
            await self._execute_with_retry(self.jira_client.add_comment, ticket_key, comment_text)

            logger.info(f"Added comment to ticket {ticket_key}")
            return True

        except Exception as e:
            logger.error(f"Failed to add comment to ticket {ticket_key}: {e}")
            return False

    async def get_pr_ticket_mappings(self, pr_numbers: List[int] = None) -> List[Dict[str, Any]]:
        """Get PR to ticket mappings from database."""
        try:
            from ..database.connection import get_database

            db = await get_database()

            filters = {}
            if pr_numbers:
                # Note: This is a simplified approach. In practice, you might need
                # to use a more complex query for filtering by multiple PR numbers
                filters = None  # Get all and filter in Python for now

            result = await db.select(table="pr_ticket_mappings", filters=filters, select_fields="*")

            if not result["success"]:
                logger.error(f"Failed to get PR-ticket mappings: {result['error']}")
                return []

            mappings = result["data"] or []

            # Filter by PR numbers if specified
            if pr_numbers:
                mappings = [m for m in mappings if m["pr_number"] in pr_numbers]

            return mappings

        except Exception as e:
            logger.error(f"Error getting PR-ticket mappings: {e}")
            return []
