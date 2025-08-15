"""
Comprehensive usage examples for the Slack Message Templates system.
Demonstrates how to use each template type with realistic scenarios.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Import template classes
# Import available template classes
try:
    from devsync_ai.templates.standup_template import StandupTemplate
except ImportError:
    print("StandupTemplate not available")
    StandupTemplate = None

try:
    from devsync_ai.templates.pr_templates import (
        NewPRTemplate, ReadyForReviewTemplate, ApprovedPRTemplate,
        ConflictsTemplate, MergedPRTemplate, ClosedPRTemplate
    )
except ImportError:
    print("PR templates not available")
    NewPRTemplate = ReadyForReviewTemplate = ApprovedPRTemplate = None
    ConflictsTemplate = MergedPRTemplate = ClosedPRTemplate = None

try:
    from devsync_ai.templates.jira_templates import JIRATemplate
    # Create aliases for different JIRA states
    StatusChangeTemplate = JIRATemplate
    PriorityChangeTemplate = JIRATemplate
    AssignmentTemplate = JIRATemplate
    CommentTemplate = JIRATemplate
    BlockerTemplate = JIRATemplate
    SprintChangeTemplate = JIRATemplate
except ImportError:
    print("JIRA templates not available")
    JIRATemplate = None

try:
    from devsync_ai.templates.alert_templates import AlertTemplate
    # Create aliases for different alert types
    BuildFailureTemplate = AlertTemplate
    DeploymentIssueTemplate = AlertTemplate
    SecurityVulnerabilityTemplate = AlertTemplate
    ServiceOutageTemplate = AlertTemplate
    CriticalBugTemplate = AlertTemplate
except ImportError:
    print("Alert templates not available")
    AlertTemplate = None

# Mock classes for demonstration if not available
class MockTemplateConfig:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class MockSlackMessage:
    def __init__(self, blocks=None, text=""):
        self.blocks = blocks or []
        self.text = text

class MockTemplate:
    def __init__(self, config=None):
        self.config = config
    
    def format_message(self, data):
        return MockSlackMessage(
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "Mock message"}}],
            text="Mock fallback text"
        )

# Use mock classes if real ones aren't available
TemplateConfig = MockTemplateConfig
if not StandupTemplate:
    StandupTemplate = MockTemplate
if not PRTemplate:
    NewPRTemplate = ReadyForReviewTemplate = ApprovedPRTemplate = ConflictsTemplate = MergedPRTemplate = ClosedPRTemplate = MockTemplate
if not JIRATemplate:
    StatusChangeTemplate = PriorityChangeTemplate = AssignmentTemplate = CommentTemplate = BlockerTemplate = SprintChangeTemplate = MockTemplate
if not AlertTemplate:
    BuildFailureTemplate = DeploymentIssueTemplate = SecurityVulnerabilityTemplate = ServiceOutageTemplate = CriticalBugTemplate = MockTemplate


def demonstrate_standup_templates():
    """Demonstrate standup template usage with various scenarios."""
    print("=== STANDUP TEMPLATE EXAMPLES ===\n")
    
    # Basic configuration
    config = TemplateConfig(
        team_id="engineering",
        branding={"team_name": "Engineering Team", "logo_emoji": "⚙️"},
        interactive_elements=True
    )
    
    template = StandupTemplate(config=config)
    
    # Example 1: Regular daily standup
    print("1. Regular Daily Standup:")
    standup_data = {
        "date": "2025-08-14",
        "team": "Engineering Team",
        "team_members": [
            {
                "name": "Alice Johnson",
                "status": "active",
                "yesterday": [
                    "Completed user authentication API",
                    "Fixed bug in payment processing",
                    "Code review for PR #234"
                ],
                "today": [
                    "Implement password reset functionality",
                    "Start work on dashboard redesign"
                ],
                "blockers": []
            },
            {
                "name": "Bob Smith",
                "status": "active",
                "yesterday": [
                    "Database migration for user profiles",
                    "Performance optimization for search"
                ],
                "today": [
                    "Continue search optimization",
                    "Meeting with product team"
                ],
                "blockers": [
                    "Waiting for API documentation from external team"
                ]
            },
            {
                "name": "Carol Davis",
                "status": "away",
                "yesterday": [],
                "today": [],
                "blockers": []
            }
        ],
        "stats": {
            "prs_merged": 8,
            "prs_open": 12,
            "tickets_completed": 15,
            "tickets_in_progress": 23,
            "commits": 47
        },
        "action_items": [
            {
                "description": "Schedule architecture review meeting",
                "assignee": "Alice Johnson",
                "due_date": "2025-08-16"
            },
            {
                "description": "Update deployment documentation",
                "assignee": "Bob Smith",
                "due_date": "2025-08-15"
            }
        ]
    }
    
    message = template.format_message(standup_data)
    print(f"Generated message with {len(message.blocks)} blocks")
    print(f"Fallback text: {message.text[:100]}...")
    print()
    
    # Example 2: Sprint retrospective standup
    print("2. Sprint Retrospective Standup:")
    retrospective_data = {
        "date": "2025-08-14",
        "team": "Engineering Team",
        "team_members": [
            {
                "name": "Alice Johnson",
                "status": "active",
                "yesterday": [
                    "Sprint demo preparation",
                    "Retrospective notes compilation"
                ],
                "today": [
                    "Sprint planning for next iteration",
                    "Backlog grooming"
                ],
                "blockers": []
            }
        ],
        "stats": {
            "prs_merged": 25,
            "prs_open": 3,
            "tickets_completed": 34,
            "tickets_in_progress": 5,
            "commits": 156
        },
        "sprint_info": {
            "name": "Sprint 23",
            "completed": True,
            "velocity": 42,
            "burndown_complete": True
        }
    }
    
    message = template.format_message(retrospective_data)
    print(f"Generated retrospective message with {len(message.blocks)} blocks")
    print()


def demonstrate_pr_templates():
    """Demonstrate PR template usage with different PR states."""
    print("=== PR TEMPLATE EXAMPLES ===\n")
    
    config = TemplateConfig(team_id="development", interactive_elements=True)
    
    # Example 1: New PR created
    print("1. New PR Created:")
    new_pr_template = NewPRTemplate(config=config)
    new_pr_data = {
        "pr": {
            "number": 456,
            "title": "Add user profile management feature",
            "description": "Implements comprehensive user profile management including avatar upload, personal information editing, and privacy settings.",
            "author": "alice.johnson",
            "url": "https://github.com/company/repo/pull/456",
            "reviewers": ["bob.smith", "carol.davis"],
            "files_changed": 12,
            "additions": 342,
            "deletions": 28,
            "draft": False,
            "jira_tickets": ["PROJ-123", "PROJ-124"],
            "ci_status": "pending"
        },
        "action": "opened"
    }
    
    message = new_pr_template.format_message(new_pr_data)
    print(f"Generated new PR message with {len(message.blocks)} blocks")
    print()
    
    # Example 2: PR ready for review
    print("2. PR Ready for Review:")
    ready_template = ReadyForReviewTemplate(config=config)
    ready_data = {
        "pr": {
            "number": 456,
            "title": "Add user profile management feature",
            "author": "alice.johnson",
            "url": "https://github.com/company/repo/pull/456",
            "reviewers": ["bob.smith", "carol.davis"],
            "draft": False,
            "ci_status": "passing",
            "checks_passing": True,
            "ready_for_review": True
        },
        "action": "ready_for_review"
    }
    
    message = ready_template.format_message(ready_data)
    print(f"Generated ready for review message with {len(message.blocks)} blocks")
    print()
    
    # Example 3: PR approved and ready to merge
    print("3. PR Approved:")
    approved_template = ApprovedPRTemplate(config=config)
    approved_data = {
        "pr": {
            "number": 456,
            "title": "Add user profile management feature",
            "author": "alice.johnson",
            "url": "https://github.com/company/repo/pull/456",
            "approved_by": ["bob.smith", "carol.davis"],
            "ci_status": "passing",
            "mergeable": True,
            "required_approvals": 2,
            "current_approvals": 2
        },
        "action": "approved"
    }
    
    message = approved_template.format_message(approved_data)
    print(f"Generated approved PR message with {len(message.blocks)} blocks")
    print()
    
    # Example 4: PR has conflicts
    print("4. PR Has Conflicts:")
    conflicts_template = ConflictsTemplate(config=config)
    conflicts_data = {
        "pr": {
            "number": 456,
            "title": "Add user profile management feature",
            "author": "alice.johnson",
            "url": "https://github.com/company/repo/pull/456",
            "has_conflicts": True,
            "conflicted_files": [
                "src/components/UserProfile.tsx",
                "src/api/userService.ts"
            ],
            "base_branch": "main"
        },
        "action": "has_conflicts"
    }
    
    message = conflicts_template.format_message(conflicts_data)
    print(f"Generated conflicts message with {len(message.blocks)} blocks")
    print()
    
    # Example 5: PR merged successfully
    print("5. PR Merged:")
    merged_template = MergedPRTemplate(config=config)
    merged_data = {
        "pr": {
            "number": 456,
            "title": "Add user profile management feature",
            "author": "alice.johnson",
            "url": "https://github.com/company/repo/pull/456",
            "merged_by": "bob.smith",
            "merged_at": "2025-08-14T15:30:00Z",
            "target_branch": "main",
            "deployment_status": "pending"
        },
        "action": "merged"
    }
    
    message = merged_template.format_message(merged_data)
    print(f"Generated merged PR message with {len(message.blocks)} blocks")
    print()


def demonstrate_jira_templates():
    """Demonstrate JIRA template usage with different ticket events."""
    print("=== JIRA TEMPLATE EXAMPLES ===\n")
    
    config = TemplateConfig(team_id="product", interactive_elements=True)
    
    # Example 1: Status change
    print("1. Ticket Status Change:")
    status_template = StatusChangeTemplate(config=config)
    status_data = {
        "ticket": {
            "key": "PROJ-789",
            "summary": "Implement user notification preferences",
            "assignee": "alice.johnson",
            "priority": "High",
            "url": "https://company.atlassian.net/browse/PROJ-789",
            "status": {
                "from": "In Progress",
                "to": "In Review"
            }
        },
        "change_type": "status_change",
        "changed_by": "alice.johnson"
    }
    
    message = status_template.format_message(status_data)
    print(f"Generated status change message with {len(message.blocks)} blocks")
    print()
    
    # Example 2: Priority escalation
    print("2. Priority Change:")
    priority_template = PriorityChangeTemplate(config=config)
    priority_data = {
        "ticket": {
            "key": "PROJ-790",
            "summary": "Critical security vulnerability in authentication",
            "assignee": "bob.smith",
            "url": "https://company.atlassian.net/browse/PROJ-790",
            "priority_change": {
                "from": "Medium",
                "to": "Blocker"
            }
        },
        "change_type": "priority_change",
        "changed_by": "product.manager"
    }
    
    message = priority_template.format_message(priority_data)
    print(f"Generated priority change message with {len(message.blocks)} blocks")
    print()
    
    # Example 3: New comment added
    print("3. Comment Added:")
    comment_template = CommentTemplate(config=config)
    comment_data = {
        "ticket": {
            "key": "PROJ-789",
            "summary": "Implement user notification preferences",
            "url": "https://company.atlassian.net/browse/PROJ-789",
            "comments": [
                {
                    "author": "carol.davis",
                    "text": "I've reviewed the implementation and it looks good. Just need to add unit tests for the email notification logic.",
                    "created": "2025-08-14T14:30:00Z"
                }
            ]
        },
        "change_type": "comment_added"
    }
    
    message = comment_template.format_message(comment_data)
    print(f"Generated comment message with {len(message.blocks)} blocks")
    print()
    
    # Example 4: Blocker identified
    print("4. Blocker Identified:")
    blocker_template = BlockerTemplate(config=config)
    blocker_data = {
        "ticket": {
            "key": "PROJ-791",
            "summary": "Database migration for user preferences",
            "assignee": "bob.smith",
            "priority": "High",
            "url": "https://company.atlassian.net/browse/PROJ-791"
        },
        "blocker": {
            "type": "identified",
            "description": "Database schema changes require DBA approval and maintenance window scheduling"
        },
        "change_type": "blocker_identified"
    }
    
    message = blocker_template.format_message(blocker_data)
    print(f"Generated blocker message with {len(message.blocks)} blocks")
    print()


def demonstrate_alert_templates():
    """Demonstrate alert template usage with different alert types."""
    print("=== ALERT TEMPLATE EXAMPLES ===\n")
    
    config = TemplateConfig(team_id="sre", interactive_elements=True)
    
    # Example 1: Build failure
    print("1. Build Failure Alert:")
    build_template = BuildFailureTemplate(config=config)
    build_data = {
        "alert": {
            "id": "BUILD-FAIL-001",
            "type": "build_failure",
            "severity": "high",
            "title": "Main branch build failed",
            "description": "The main branch build failed due to test failures in the authentication module.",
            "created_at": "2025-08-14T16:45:00Z",
            "assigned_to": "alice.johnson"
        },
        "build_info": {
            "branch": "main",
            "commit": "a1b2c3d4",
            "pipeline_url": "https://ci.company.com/build/12345",
            "failed_tests": [
                "test_user_login",
                "test_password_reset"
            ]
        }
    }
    
    message = build_template.format_message(build_data)
    print(f"Generated build failure message with {len(message.blocks)} blocks")
    print()
    
    # Example 2: Deployment issue
    print("2. Deployment Issue Alert:")
    deployment_template = DeploymentIssueTemplate(config=config)
    deployment_data = {
        "alert": {
            "id": "DEPLOY-ISSUE-002",
            "type": "deployment_issue",
            "severity": "critical",
            "title": "Production deployment failed",
            "description": "Production deployment failed during database migration step.",
            "created_at": "2025-08-14T17:00:00Z",
            "assigned_to": "sre.oncall"
        },
        "deployment_info": {
            "environment": "production",
            "version": "v2.1.4",
            "rollback_available": True,
            "failed_step": "database_migration"
        }
    }
    
    message = deployment_template.format_message(deployment_data)
    print(f"Generated deployment issue message with {len(message.blocks)} blocks")
    print()
    
    # Example 3: Security vulnerability
    print("3. Security Vulnerability Alert:")
    security_template = SecurityVulnerabilityTemplate(config=config)
    security_data = {
        "alert": {
            "id": "SEC-VULN-003",
            "type": "security_vulnerability",
            "severity": "critical",
            "title": "Critical vulnerability in authentication library",
            "description": "A critical vulnerability has been discovered in the authentication library that could allow unauthorized access.",
            "created_at": "2025-08-14T17:15:00Z",
            "assigned_to": "security.team"
        },
        "security_info": {
            "cve_id": "CVE-2025-12345",
            "cvss_score": 9.8,
            "attack_vector": "Network",
            "affected_versions": ["v2.0.0", "v2.1.0", "v2.1.1", "v2.1.2", "v2.1.3"]
        }
    }
    
    message = security_template.format_message(security_data)
    print(f"Generated security vulnerability message with {len(message.blocks)} blocks")
    print()
    
    # Example 4: Service outage
    print("4. Service Outage Alert:")
    outage_template = ServiceOutageTemplate(config=config)
    outage_data = {
        "alert": {
            "id": "OUTAGE-004",
            "type": "service_outage",
            "severity": "critical",
            "title": "API Gateway service outage",
            "description": "The API Gateway is experiencing a complete outage affecting all services.",
            "created_at": "2025-08-14T17:30:00Z",
            "assigned_to": "sre.oncall"
        },
        "outage_info": {
            "services": ["API Gateway", "User Service", "Payment Service"],
            "users_affected": 50000,
            "status_page": "https://status.company.com",
            "estimated_resolution": "2025-08-14T18:30:00Z"
        }
    }
    
    message = outage_template.format_message(outage_data)
    print(f"Generated service outage message with {len(message.blocks)} blocks")
    print()


def demonstrate_template_factory_usage():
    """Demonstrate using templates directly (factory pattern simulation)."""
    print("=== TEMPLATE USAGE EXAMPLES ===\n")
    
    # Initialize configuration
    config = TemplateConfig(
        team_id="engineering",
        branding={"team_name": "Engineering Team", "logo_emoji": "🚀"},
        interactive_elements=True,
        accessibility_mode=False
    )
    
    # Example 1: Create templates directly
    print("1. Direct Template Creation:")
    
    # Different template types and their data
    template_examples = [
        ("standup", StandupTemplate, {
            "date": "2025-08-14",
            "team": "Engineering Team",
            "team_members": [
                {
                    "name": "Alice",
                    "yesterday": ["Completed feature X"],
                    "today": ["Working on feature Y"],
                    "blockers": []
                }
            ]
        }),
        ("pr", NewPRTemplate, {
            "pr": {
                "number": 123,
                "title": "Add new feature",
                "author": "alice.johnson"
            },
            "action": "opened"
        }),
        ("jira", StatusChangeTemplate, {
            "ticket": {
                "key": "PROJ-456",
                "summary": "Fix critical bug"
            },
            "change_type": "status_change"
        }),
        ("alert", BuildFailureTemplate, {
            "alert": {
                "id": "BUILD-001",
                "type": "build_failure",
                "severity": "high",
                "title": "Build failed on main branch"
            }
        })
    ]
    
    for template_name, template_class, event_data in template_examples:
        try:
            template = template_class(config=config)
            message = template.format_message(event_data)
            print(f"✅ {template_name}: Generated message with {len(message.blocks)} blocks")
        except Exception as e:
            print(f"❌ {template_name}: Failed to generate message - {e}")
    
    print()
    
    # Example 2: Batch processing simulation
    print("2. Batch Processing Simulation:")
    
    batch_data = [
        {"date": "2025-08-14", "team": "Team A", "team_members": []},
        {"date": "2025-08-15", "team": "Team B", "team_members": []},
        {"date": "2025-08-16", "team": "Team C", "team_members": []}
    ]
    
    template = StandupTemplate(config=config)
    messages = []
    
    for data in batch_data:
        try:
            message = template.format_message(data)
            messages.append(message)
        except Exception as e:
            print(f"❌ Failed to process batch item: {e}")
    
    print(f"Processed {len(messages)} messages in batch")
    
    for i, message in enumerate(messages):
        print(f"  Message {i+1}: {len(message.blocks)} blocks, fallback: '{message.text[:50]}...'")
    
    print()


def demonstrate_configuration_examples():
    """Demonstrate different configuration options."""
    print("=== CONFIGURATION EXAMPLES ===\n")
    
    # Example 1: Basic configuration
    print("1. Basic Configuration:")
    basic_config = TemplateConfig(team_id="basic_team")
    template = StandupTemplate(config=basic_config)
    
    basic_data = {
        "date": "2025-08-14",
        "team": "Basic Team",
        "team_members": []
    }
    
    message = template.format_message(basic_data)
    print(f"Basic config message: {len(message.blocks)} blocks")
    print()
    
    # Example 2: Branded configuration
    print("2. Branded Configuration:")
    branded_config = TemplateConfig(
        team_id="branded_team",
        branding={
            "team_name": "🚀 Rocket Team",
            "logo_emoji": "🚀",
            "primary_color": "#FF6B35",
            "accent_color": "#004E89"
        },
        emoji_set={
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "info": "ℹ️",
            "in_progress": "🔄"
        }
    )
    
    branded_template = StandupTemplate(config=branded_config)
    message = branded_template.format_message(basic_data)
    print(f"Branded config message: {len(message.blocks)} blocks")
    print()
    
    # Example 3: Accessibility-focused configuration
    print("3. Accessibility Configuration:")
    accessible_config = TemplateConfig(
        team_id="accessible_team",
        accessibility_mode=True,
        interactive_elements=False,  # Disable for screen readers
        fallback_text_detailed=True
    )
    
    accessible_template = StandupTemplate(config=accessible_config)
    message = accessible_template.format_message(basic_data)
    print(f"Accessible config message: {len(message.blocks)} blocks")
    print(f"Detailed fallback text: '{message.text}'")
    print()
    
    # Example 4: Performance-optimized configuration
    print("4. Performance Configuration:")
    performance_config = TemplateConfig(
        team_id="performance_team",
        caching_enabled=True,
        cache_ttl=3600,  # 1 hour
        batch_processing=True,
        threading_enabled=True
    )
    
    performance_template = StandupTemplate(config=performance_config)
    message = performance_template.format_message(basic_data)
    print(f"Performance config message: {len(message.blocks)} blocks")
    print()


def demonstrate_error_handling():
    """Demonstrate error handling and graceful degradation."""
    print("=== ERROR HANDLING EXAMPLES ===\n")
    
    config = TemplateConfig(team_id="error_test")
    template = StandupTemplate(config=config)
    
    # Example 1: Missing required data
    print("1. Missing Required Data:")
    try:
        incomplete_data = {}  # Missing all required fields
        message = template.format_message(incomplete_data)
        print(f"✅ Handled missing data gracefully: {len(message.blocks)} blocks")
        print(f"Fallback message: '{message.text}'")
    except Exception as e:
        print(f"❌ Failed to handle missing data: {e}")
    print()
    
    # Example 2: Malformed data types
    print("2. Malformed Data Types:")
    try:
        malformed_data = {
            "date": 20250814,  # Should be string
            "team": ["not", "a", "string"],  # Should be string
            "team_members": "not a list"  # Should be list
        }
        message = template.format_message(malformed_data)
        print(f"✅ Handled malformed data gracefully: {len(message.blocks)} blocks")
    except Exception as e:
        print(f"❌ Failed to handle malformed data: {e}")
    print()
    
    # Example 3: Unicode and special characters
    print("3. Unicode and Special Characters:")
    try:
        unicode_data = {
            "date": "2025-08-14",
            "team": "🌟 Unicode Team 🌟",
            "team_members": [
                {
                    "name": "José María García-López",
                    "yesterday": ["Implemented αβγ algorithm"],
                    "today": ["Working on 日本語 support"],
                    "blockers": ["Need ñ character support"]
                }
            ]
        }
        message = template.format_message(unicode_data)
        print(f"✅ Handled unicode data gracefully: {len(message.blocks)} blocks")
    except Exception as e:
        print(f"❌ Failed to handle unicode data: {e}")
    print()


def main():
    """Run all template usage examples."""
    print("SLACK MESSAGE TEMPLATES - COMPREHENSIVE USAGE EXAMPLES")
    print("=" * 60)
    print()
    
    try:
        demonstrate_standup_templates()
        demonstrate_pr_templates()
        demonstrate_jira_templates()
        demonstrate_alert_templates()
        demonstrate_template_factory_usage()
        demonstrate_configuration_examples()
        demonstrate_error_handling()
        
        print("=" * 60)
        print("✅ All template examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Example demonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()