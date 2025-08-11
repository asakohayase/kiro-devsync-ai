"""Tests for JIRA service functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from jira import JIRAError

from devsync_ai.services.jira import JiraService, JiraAPIError, JiraConnectionInfo
from devsync_ai.models.core import JiraTicket


class TestJiraService:
    """Test cases for JiraService class."""

    @pytest.fixture
    def mock_jira_client(self):
        """Mock JIRA client for testing."""
        with patch("devsync_ai.services.jira.JIRA") as mock_jira:
            mock_instance = Mock()
            mock_jira.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def jira_service(self):
        """Create JiraService instance for testing."""
        return JiraService(
            server_url="https://test.atlassian.net", username="test@example.com", token="test_token"
        )

    @pytest.fixture
    def mock_jira_issue(self):
        """Create mock JIRA issue for testing."""
        issue = Mock()
        issue.key = "TEST-123"
        issue.fields = Mock()
        issue.fields.summary = "Test issue summary"
        issue.fields.status = Mock()
        issue.fields.status.name = "In Progress"
        issue.fields.assignee = Mock()
        issue.fields.assignee.displayName = "John Doe"
        issue.fields.priority = Mock()
        issue.fields.priority.name = "High"
        issue.fields.labels = []
        issue.fields.created = "2024-01-01T10:00:00.000+0000"
        issue.fields.updated = "2024-01-02T15:30:00.000+0000"
        issue.fields.customfield_10016 = 5  # Story points
        issue.fields.customfield_10020 = None  # Sprint field
        issue.fields.customfield_10010 = None  # Alternative sprint field
        issue.fields.sprint = None  # Another sprint field
        issue.changelog = None
        return issue

    def test_init_with_credentials(self):
        """Test JiraService initialization with credentials."""
        service = JiraService(
            server_url="https://test.atlassian.net", username="test@example.com", token="test_token"
        )

        assert service.server_url == "https://test.atlassian.net"
        assert service.username == "test@example.com"
        assert service.token == "test_token"
        assert service._jira_client is None

    def test_init_without_credentials(self):
        """Test JiraService initialization without credentials."""
        with patch("devsync_ai.services.jira.settings") as mock_settings:
            mock_settings.jira_url = None
            mock_settings.jira_username = None
            mock_settings.jira_token = None

            service = JiraService()
            assert service.server_url is None
            assert service.username is None
            assert service.token is None

    def test_jira_client_property_success(self, jira_service, mock_jira_client):
        """Test successful JIRA client initialization."""
        client = jira_service.jira_client
        assert client is not None
        assert jira_service._jira_client is not None

    def test_jira_client_property_missing_credentials(self):
        """Test JIRA client initialization with missing credentials."""
        service = JiraService(server_url=None, username=None, token=None)

        with pytest.raises(JiraAPIError) as exc_info:
            _ = service.jira_client

        assert "JIRA credentials not configured" in str(exc_info.value)

    def test_jira_client_property_connection_error(self, jira_service):
        """Test JIRA client initialization with connection error."""
        with patch("devsync_ai.services.jira.JIRA") as mock_jira:
            mock_jira.side_effect = JIRAError("Connection failed")

            with pytest.raises(JiraAPIError) as exc_info:
                _ = jira_service.jira_client

            assert "JIRA connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self, jira_service):
        """Test successful execution with retry logic."""
        mock_func = Mock(return_value="success")

        result = await jira_service._execute_with_retry(mock_func, "arg1", kwarg1="value1")

        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")

    @pytest.mark.asyncio
    async def test_execute_with_retry_auth_error(self, jira_service):
        """Test retry logic with authentication error (no retry)."""
        mock_func = Mock(side_effect=JIRAError("Unauthorized", status_code=401))

        with pytest.raises(JiraAPIError) as exc_info:
            await jira_service._execute_with_retry(mock_func)

        assert "authentication/permission error" in str(exc_info.value)
        assert exc_info.value.status_code == 401
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_retry_not_found_error(self, jira_service):
        """Test retry logic with not found error (no retry)."""
        mock_func = Mock(side_effect=JIRAError("Not found", status_code=404))

        with pytest.raises(JiraAPIError) as exc_info:
            await jira_service._execute_with_retry(mock_func)

        assert "resource not found" in str(exc_info.value)
        assert exc_info.value.status_code == 404
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_retry_retryable_error(self, jira_service):
        """Test retry logic with retryable error."""
        mock_func = Mock(
            side_effect=[
                JIRAError("Server error", status_code=500),
                JIRAError("Server error", status_code=500),
                "success",
            ]
        )

        with patch("asyncio.sleep"):
            result = await jira_service._execute_with_retry(mock_func, max_retries=3)

        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_retry_max_retries_exceeded(self, jira_service):
        """Test retry logic when max retries exceeded."""
        mock_func = Mock(side_effect=JIRAError("Server error", status_code=500))

        with patch("asyncio.sleep"):
            with pytest.raises(JiraAPIError) as exc_info:
                await jira_service._execute_with_retry(mock_func, max_retries=2)

        assert "after retries" in str(exc_info.value)
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_test_authentication_success(self, jira_service, mock_jira_client):
        """Test successful authentication test."""
        mock_jira_client.server_info.return_value = {
            "version": "8.20.0",
            "buildNumber": "820000",
            "serverTitle": "Test JIRA",
        }
        mock_jira_client.current_user.return_value = "test@example.com"

        result = await jira_service.test_authentication()

        assert isinstance(result, JiraConnectionInfo)
        assert result.server_url == "https://test.atlassian.net"
        assert result.username == "test@example.com"
        assert result.authenticated is True
        assert result.server_info["version"] == "8.20.0"

    @pytest.mark.asyncio
    async def test_test_authentication_failure(self, jira_service):
        """Test authentication test failure."""
        with patch.object(jira_service, "_execute_with_retry") as mock_execute:
            mock_execute.side_effect = JiraAPIError("Auth failed")

            with pytest.raises(JiraAPIError):
                await jira_service.test_authentication()

    def test_convert_jira_issue_to_model_basic(self, jira_service, mock_jira_issue):
        """Test basic JIRA issue to model conversion."""
        ticket = jira_service._convert_jira_issue_to_model(mock_jira_issue)

        assert isinstance(ticket, JiraTicket)
        assert ticket.key == "TEST-123"
        assert ticket.summary == "Test issue summary"
        assert ticket.status == "In Progress"
        assert ticket.assignee == "John Doe"
        assert ticket.priority == "High"
        assert ticket.story_points == 5
        assert ticket.blocked is False

    def test_convert_jira_issue_to_model_blocked_by_label(self, jira_service, mock_jira_issue):
        """Test JIRA issue conversion with blocked label."""
        mock_jira_issue.fields.labels = ["blocked", "urgent"]

        ticket = jira_service._convert_jira_issue_to_model(mock_jira_issue)

        assert ticket.blocked is True

    def test_convert_jira_issue_to_model_blocked_by_status(self, jira_service, mock_jira_issue):
        """Test JIRA issue conversion with blocking status."""
        mock_jira_issue.fields.status.name = "Blocked"

        ticket = jira_service._convert_jira_issue_to_model(mock_jira_issue)

        assert ticket.blocked is True

    def test_convert_jira_issue_to_model_no_assignee(self, jira_service, mock_jira_issue):
        """Test JIRA issue conversion with no assignee."""
        mock_jira_issue.fields.assignee = None

        ticket = jira_service._convert_jira_issue_to_model(mock_jira_issue)

        assert ticket.assignee is None

    def test_convert_jira_issue_to_model_conversion_error(self, jira_service):
        """Test JIRA issue conversion with error (should return minimal ticket)."""
        mock_issue = Mock()
        mock_issue.key = "TEST-456"
        mock_issue.fields = Mock()
        mock_issue.fields.summary = "Test summary"
        mock_issue.fields.status = Mock()
        mock_issue.fields.status.name = "Open"
        # Simulate error by making updated field invalid
        mock_issue.fields.updated = "invalid-date"

        ticket = jira_service._convert_jira_issue_to_model(mock_issue)

        assert ticket.key == "TEST-456"
        assert ticket.summary == "Test summary"
        assert ticket.status == "Open"
        assert ticket.blocked is False

    def test_extract_sprint_name_with_list(self, jira_service, mock_jira_issue):
        """Test sprint name extraction from list format."""
        mock_sprint = Mock()
        mock_sprint.name = "Sprint 1"
        mock_jira_issue.fields.customfield_10020 = [mock_sprint]

        sprint_name = jira_service._extract_sprint_name(mock_jira_issue)

        assert sprint_name == "Sprint 1"

    def test_extract_sprint_name_with_string(self, jira_service, mock_jira_issue):
        """Test sprint name extraction from string format."""
        mock_jira_issue.fields.customfield_10020 = [
            "com.atlassian.greenhopper.service.sprint.Sprint@123[id=1,name=Sprint 1,state=ACTIVE]"
        ]

        sprint_name = jira_service._extract_sprint_name(mock_jira_issue)

        assert sprint_name == "Sprint 1"

    def test_extract_sprint_name_no_sprint(self, jira_service, mock_jira_issue):
        """Test sprint name extraction when no sprint found."""
        mock_jira_issue.fields.customfield_10020 = None
        mock_jira_issue.fields.customfield_10010 = None

        sprint_name = jira_service._extract_sprint_name(mock_jira_issue)

        assert sprint_name is None

    @pytest.mark.asyncio
    async def test_get_projects_success(self, jira_service, mock_jira_client):
        """Test successful project retrieval."""
        mock_project1 = Mock()
        mock_project1.key = "TEST"
        mock_project1.name = "Test Project"
        mock_project1.id = "10001"
        mock_project1.projectTypeKey = "software"

        mock_project2 = Mock()
        mock_project2.key = "DEMO"
        mock_project2.name = "Demo Project"
        mock_project2.id = "10002"
        # Simulate missing projectTypeKey attribute
        del mock_project2.projectTypeKey

        mock_jira_client.projects.return_value = [mock_project1, mock_project2]

        projects = await jira_service.get_projects()

        assert len(projects) == 2
        assert projects[0]["key"] == "TEST"
        assert projects[0]["name"] == "Test Project"
        assert projects[0]["project_type"] == "software"
        assert projects[1]["key"] == "DEMO"
        assert projects[1]["project_type"] == "Unknown"

    @pytest.mark.asyncio
    async def test_get_issues_by_jql_success(self, jira_service, mock_jira_client, mock_jira_issue):
        """Test successful JQL query execution."""
        mock_jira_client.search_issues.return_value = [mock_jira_issue]

        tickets = await jira_service.get_issues_by_jql("project = TEST")

        assert len(tickets) == 1
        assert tickets[0].key == "TEST-123"
        mock_jira_client.search_issues.assert_called_once_with(
            "project = TEST", maxResults=100, expand="changelog"
        )

    @pytest.mark.asyncio
    async def test_get_active_tickets_with_project(self, jira_service):
        """Test getting active tickets for specific project."""
        with patch.object(jira_service, "get_issues_by_jql") as mock_jql:
            mock_jql.return_value = []

            await jira_service.get_active_tickets(project_key="TEST")

            mock_jql.assert_called_once()
            jql_query = mock_jql.call_args[0][0]
            assert 'project = "TEST"' in jql_query
            assert 'status != "Done"' in jql_query

    @pytest.mark.asyncio
    async def test_get_active_tickets_with_assignee(self, jira_service):
        """Test getting active tickets for specific assignee."""
        with patch.object(jira_service, "get_issues_by_jql") as mock_jql:
            mock_jql.return_value = []

            await jira_service.get_active_tickets(assignee="john.doe")

            mock_jql.assert_called_once()
            jql_query = mock_jql.call_args[0][0]
            assert 'assignee = "john.doe"' in jql_query

    @pytest.mark.asyncio
    async def test_get_active_tickets_current_user(self, jira_service):
        """Test getting active tickets for current user."""
        with patch.object(jira_service, "get_issues_by_jql") as mock_jql:
            mock_jql.return_value = []

            await jira_service.get_active_tickets(assignee="currentuser")

            mock_jql.assert_called_once()
            jql_query = mock_jql.call_args[0][0]
            assert "assignee = currentUser()" in jql_query

    @pytest.mark.asyncio
    async def test_get_tickets_in_sprint(self, jira_service):
        """Test getting tickets in specific sprint."""
        with patch.object(jira_service, "get_issues_by_jql") as mock_jql:
            mock_jql.return_value = []

            await jira_service.get_tickets_in_sprint(123)

            mock_jql.assert_called_once_with("sprint = 123 ORDER BY rank ASC")

    @pytest.mark.asyncio
    async def test_get_current_sprint_tickets_success(self, jira_service, mock_jira_client):
        """Test getting current sprint tickets successfully."""
        mock_sprint = Mock()
        mock_sprint.id = 456
        mock_jira_client.sprints.return_value = [mock_sprint]

        with patch.object(jira_service, "get_tickets_in_sprint") as mock_get_tickets:
            mock_get_tickets.return_value = []

            await jira_service.get_current_sprint_tickets(123)

            mock_jira_client.sprints.assert_called_once_with(123, state="active")
            mock_get_tickets.assert_called_once_with(456)

    @pytest.mark.asyncio
    async def test_get_current_sprint_tickets_no_active_sprint(
        self, jira_service, mock_jira_client
    ):
        """Test getting current sprint tickets when no active sprint."""
        mock_jira_client.sprints.return_value = []

        tickets = await jira_service.get_current_sprint_tickets(123)

        assert tickets == []

    @pytest.mark.asyncio
    async def test_detect_blocked_tickets_explicit_blocking(self, jira_service):
        """Test blocked ticket detection with explicitly blocked ticket."""
        blocked_ticket = JiraTicket(
            key="TEST-123",
            summary="Blocked ticket",
            status="In Progress",
            assignee="John Doe",
            priority="High",
            story_points=5,
            sprint="Sprint 1",
            blocked=True,
            last_updated=datetime.now() - timedelta(days=1),
            time_in_status=timedelta(days=3),
        )

        blocked_tickets = await jira_service.detect_blocked_tickets([blocked_ticket])

        assert len(blocked_tickets) == 1
        assert blocked_tickets[0]["severity"] == "high"
        assert "Explicitly marked as blocked" in blocked_tickets[0]["reasons"]

    @pytest.mark.asyncio
    async def test_detect_blocked_tickets_stale_status(self, jira_service):
        """Test blocked ticket detection with stale status."""
        stale_ticket = JiraTicket(
            key="TEST-456",
            summary="Stale ticket",
            status="In Progress",
            assignee="Jane Doe",
            priority="Medium",
            story_points=3,
            sprint="Sprint 1",
            blocked=False,
            last_updated=datetime.now() - timedelta(days=2),
            time_in_status=timedelta(days=10),  # Stale
        )

        blocked_tickets = await jira_service.detect_blocked_tickets([stale_ticket], stale_days=7)

        assert len(blocked_tickets) == 1
        assert blocked_tickets[0]["severity"] == "medium"
        assert any(
            "In 'In Progress' status for 10 days" in reason
            for reason in blocked_tickets[0]["reasons"]
        )

    @pytest.mark.asyncio
    async def test_detect_blocked_tickets_blocking_status(self, jira_service):
        """Test blocked ticket detection with blocking status name."""
        blocking_ticket = JiraTicket(
            key="TEST-789",
            summary="Waiting ticket",
            status="Waiting for Approval",
            assignee="Bob Smith",
            priority="Low",
            story_points=2,
            sprint="Sprint 1",
            blocked=False,
            last_updated=datetime.now() - timedelta(days=1),
            time_in_status=timedelta(days=2),
        )

        blocked_tickets = await jira_service.detect_blocked_tickets([blocking_ticket])

        assert len(blocked_tickets) == 1
        assert blocked_tickets[0]["severity"] == "high"
        assert any(
            "Status indicates blocking" in reason for reason in blocked_tickets[0]["reasons"]
        )

    @pytest.mark.asyncio
    async def test_detect_blocked_tickets_no_blockers(self, jira_service):
        """Test blocked ticket detection with no blockers found."""
        normal_ticket = JiraTicket(
            key="TEST-999",
            summary="Normal ticket",
            status="In Progress",
            assignee="Alice Johnson",
            priority="Medium",
            story_points=3,
            sprint="Sprint 1",
            blocked=False,
            last_updated=datetime.now() - timedelta(hours=2),
            time_in_status=timedelta(days=2),
        )

        blocked_tickets = await jira_service.detect_blocked_tickets([normal_ticket])

        assert len(blocked_tickets) == 0

    @pytest.mark.asyncio
    async def test_detect_blocked_tickets_sorting(self, jira_service):
        """Test blocked ticket detection sorting by severity and days."""
        high_severity_ticket = JiraTicket(
            key="TEST-HIGH",
            summary="High severity",
            status="Blocked",
            assignee="User1",
            priority="High",
            story_points=5,
            sprint="Sprint 1",
            blocked=False,
            last_updated=datetime.now() - timedelta(days=1),
            time_in_status=timedelta(days=5),
        )

        medium_severity_ticket = JiraTicket(
            key="TEST-MED",
            summary="Medium severity",
            status="In Progress",
            assignee="User2",
            priority="Medium",
            story_points=3,
            sprint="Sprint 1",
            blocked=False,
            last_updated=datetime.now() - timedelta(days=1),
            time_in_status=timedelta(days=10),  # More days but lower severity
        )

        tickets = [medium_severity_ticket, high_severity_ticket]
        blocked_tickets = await jira_service.detect_blocked_tickets(tickets, stale_days=7)

        assert len(blocked_tickets) == 2
        # High severity should come first despite fewer days
        assert blocked_tickets[0]["ticket"].key == "TEST-HIGH"
        assert blocked_tickets[0]["severity"] == "high"
        assert blocked_tickets[1]["ticket"].key == "TEST-MED"
        assert blocked_tickets[1]["severity"] == "medium"

    @pytest.mark.asyncio
    async def test_get_ticket_details_success(
        self, jira_service, mock_jira_client, mock_jira_issue
    ):
        """Test successful ticket details retrieval."""
        mock_jira_client.issue.return_value = mock_jira_issue

        ticket = await jira_service.get_ticket_details("TEST-123")

        assert ticket is not None
        assert ticket.key == "TEST-123"
        mock_jira_client.issue.assert_called_once_with("TEST-123", expand="changelog")

    @pytest.mark.asyncio
    async def test_get_ticket_details_not_found(self, jira_service):
        """Test ticket details retrieval when ticket not found."""
        with patch.object(jira_service, "_execute_with_retry") as mock_execute:
            mock_execute.side_effect = JiraAPIError("Not found", status_code=404)

            ticket = await jira_service.get_ticket_details("NONEXISTENT-123")

            assert ticket is None

    @pytest.mark.asyncio
    async def test_get_ticket_details_other_error(self, jira_service):
        """Test ticket details retrieval with other error."""
        with patch.object(jira_service, "_execute_with_retry") as mock_execute:
            mock_execute.side_effect = JiraAPIError("Server error", status_code=500)

            with pytest.raises(JiraAPIError):
                await jira_service.get_ticket_details("TEST-123")

    @pytest.mark.asyncio
    async def test_sync_tickets_with_project(self, jira_service):
        """Test ticket synchronization with project filter."""
        mock_tickets = [
            JiraTicket(
                key="TEST-1",
                summary="Test 1",
                status="In Progress",
                assignee="User1",
                priority="High",
                story_points=5,
                sprint="Sprint 1",
                blocked=False,
                last_updated=datetime.now(),
                time_in_status=timedelta(days=1),
            ),
            JiraTicket(
                key="TEST-2",
                summary="Test 2",
                status="Done",
                assignee="User2",
                priority="Medium",
                story_points=3,
                sprint="Sprint 1",
                blocked=False,
                last_updated=datetime.now(),
                time_in_status=timedelta(days=2),
            ),
        ]

        with patch.object(jira_service, "get_issues_by_jql") as mock_jql:
            mock_jql.return_value = mock_tickets

            with patch.object(jira_service, "detect_blocked_tickets") as mock_detect:
                mock_detect.return_value = []

                summary = await jira_service.sync_tickets(project_key="TEST")

                assert summary["total_tickets_synced"] == 2
                assert summary["blocked_tickets_detected"] == 0
                assert "In Progress" in summary["tickets_by_status"]
                assert "Done" in summary["tickets_by_status"]
                assert "User1" in summary["tickets_by_assignee"]
                assert "User2" in summary["tickets_by_assignee"]

                # Verify JQL query included project filter
                jql_query = mock_jql.call_args[0][0]
                assert 'project = "TEST"' in jql_query

    @pytest.mark.asyncio
    async def test_sync_tickets_with_updated_since(self, jira_service):
        """Test ticket synchronization with updated since filter."""
        updated_since = datetime.now() - timedelta(hours=12)

        with patch.object(jira_service, "get_issues_by_jql") as mock_jql:
            mock_jql.return_value = []

            with patch.object(jira_service, "detect_blocked_tickets") as mock_detect:
                mock_detect.return_value = []

                await jira_service.sync_tickets(updated_since=updated_since)

                jql_query = mock_jql.call_args[0][0]
                expected_date = updated_since.strftime("%Y-%m-%d %H:%M")
                assert f'updated >= "{expected_date}"' in jql_query

    @pytest.mark.asyncio
    async def test_sync_tickets_with_blocked_tickets(self, jira_service):
        """Test ticket synchronization with blocked tickets detected."""
        mock_ticket = JiraTicket(
            key="TEST-BLOCKED",
            summary="Blocked ticket",
            status="Blocked",
            assignee="User1",
            priority="High",
            story_points=5,
            sprint="Sprint 1",
            blocked=True,
            last_updated=datetime.now(),
            time_in_status=timedelta(days=5),
        )

        mock_blocked = [
            {
                "ticket": mock_ticket,
                "reasons": ["Explicitly marked as blocked"],
                "severity": "high",
                "days_in_status": 5,
            }
        ]

        with patch.object(jira_service, "get_issues_by_jql") as mock_jql:
            mock_jql.return_value = [mock_ticket]

            with patch.object(jira_service, "detect_blocked_tickets") as mock_detect:
                mock_detect.return_value = mock_blocked

                summary = await jira_service.sync_tickets()

                assert summary["total_tickets_synced"] == 1
                assert summary["blocked_tickets_detected"] == 1
                assert len(summary["blocked_tickets"]) == 1

                blocked_summary = summary["blocked_tickets"][0]
                assert blocked_summary["key"] == "TEST-BLOCKED"
                assert blocked_summary["severity"] == "high"
                assert blocked_summary["days_in_status"] == 5

    @pytest.mark.asyncio
    async def test_sync_tickets_default_time_filter(self, jira_service):
        """Test ticket synchronization with default 24-hour filter."""
        with patch.object(jira_service, "get_issues_by_jql") as mock_jql:
            mock_jql.return_value = []

            with patch.object(jira_service, "detect_blocked_tickets") as mock_detect:
                mock_detect.return_value = []

                await jira_service.sync_tickets()

                jql_query = mock_jql.call_args[0][0]
                # Should include a date filter for last 24 hours
                assert "updated >=" in jql_query
                assert "ORDER BY updated DESC" in jql_query
