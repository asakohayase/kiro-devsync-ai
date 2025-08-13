# Slack Message Templates Documentation

## Overview

The DevSync AI Slack templates provide rich, interactive message formatting for various development workflow notifications. Built using Slack's Block Kit, these templates create visually appealing and actionable messages for team communication.

## Features

- **Rich Formatting**: Uses Slack Block Kit for professional-looking messages
- **Interactive Elements**: Buttons for common actions (approve, merge, review)
- **Status Indicators**: Color-coded emojis for quick status recognition
- **Progress Tracking**: Visual progress bars and completion metrics
- **Responsive Design**: Works well on both desktop and mobile
- **Error Handling**: Graceful handling of missing or malformed data

## Template Types

### 1. Daily Standup Template

Creates comprehensive daily standup summaries with team statistics and individual updates.

#### Features:
- Team health indicators
- Sprint progress visualization
- Individual team member sections
- Action items tracking
- Interactive dashboard buttons

#### Data Structure:
```python
{
    "date": "2025-08-12",
    "team": "DevSync Team",
    "stats": {
        "prs_merged": 3,
        "prs_open": 5,
        "tickets_completed": 7,
        "tickets_in_progress": 12,
        "commits": 23
    },
    "team_members": [
        {
            "name": "Alice",
            "status": "active",  # active, away, blocked, inactive
            "yesterday": ["Completed user auth", "Fixed bug #123"],
            "today": ["Start payment integration", "Code review"],
            "blockers": []
        }
    ],
    "action_items": ["Deploy staging environment", "Update documentation"]
}
```

#### Usage:
```python
from devsync_ai.services.slack_templates import create_standup_message

message = create_standup_message(data)
# Send to Slack channel
```

### 2. PR Status Templates

Multiple specialized templates for different PR lifecycle events.

#### Available Templates:

##### New PR Template (`opened`)
- Highlights new PR creation
- Shows author and description
- Provides review assignment actions

##### Ready for Review Template (`ready_for_review`)
- Emphasizes review readiness
- Lists assigned reviewers
- Includes review action buttons

##### Approved PR Template (`approved`)
- Celebrates approval
- Shows merge readiness checklist
- Provides merge action button

##### Conflicts Template (`has_conflicts`)
- Warning styling for conflicts
- Resolution guidance
- Help and pause actions

##### Merged PR Template (`merged`)
- Success celebration
- Deployment status
- JIRA ticket updates
- Post-merge actions

##### Closed PR Template (`closed`)
- Closure notification
- Reason for closure
- Reopen and cleanup actions

#### Data Structure:
```python
{
    "pr": {
        "id": 123,
        "title": "Add user authentication",
        "description": "Implements OAuth2 login flow",
        "author": "alice",
        "status": "open",  # open, merged, closed
        "draft": false,
        "reviewers": ["bob", "carol"],
        "approved_by": ["bob"],
        "changes_requested_by": [],
        "has_conflicts": false,
        "files_changed": 12,
        "additions": 234,
        "deletions": 45,
        "created_at": "2025-08-12T10:00:00Z",
        "updated_at": "2025-08-12T14:30:00Z",
        "jira_tickets": ["DP-123", "DP-124"],
        "ci_status": "passing",  # passing, failing, pending, unknown
        "required_approvals": 1
    },
    "action": "opened",  # opened, ready_for_review, approved, etc.
    "close_reason": "Superseded by another PR",  # for closed PRs
    "deployment_status": "deployed"  # for merged PRs
}
```

#### Usage:
```python
from devsync_ai.services.pr_status_templates import create_pr_message_by_action

message = create_pr_message_by_action(data)
# Send to Slack channel
```

### 3. JIRA Ticket Templates

Comprehensive templates for various JIRA ticket lifecycle events with rich formatting and interactive elements.

#### Available Templates:

##### Status Change Template (`status_change`)
- Visual status transition (📋 To Do → ⏳ In Progress)
- Workflow context messages
- Time tracking information
- Status-specific action buttons

##### Priority Change Template (`priority_change`)
- Priority transition visualization with emojis
- Urgency indicators and messages
- Escalation context

##### Assignment Change Template (`assignment_change`)
- Assignment transition display
- New assignee notifications
- Reassignment context

##### Comment Template (`comment_added`)
- Latest comment preview
- Comment history summary
- Author and timestamp information

##### Blocker Template (`blocker_identified`/`blocker_resolved`)
- Blocker identification/resolution messages
- Escalation and help assignment actions
- Resume work buttons for resolved blockers

##### Sprint Change Template (`sprint_change`)
- Sprint transition visualization
- Sprint context (dates, capacity, committed points)
- Sprint planning information

#### Data Structure:
```python
{
    "ticket": {
        "key": "DP-123",
        "summary": "Implement user dashboard",
        "description": "Create responsive dashboard...",
        "status": {
            "from": "In Progress",
            "to": "Done"
        },
        "priority": "High",
        "assignee": "alice",
        "reporter": "bob",
        "sprint": "Sprint 5",
        "epic": "User Management",
        "story_points": 8,
        "time_spent": "6h 30m",
        "time_remaining": "0h",
        "created": "2025-08-10T09:00:00Z",
        "updated": "2025-08-12T15:45:00Z",
        "comments": [
            {
                "author": "alice",
                "text": "Dashboard implementation complete",
                "created": "2025-08-12T15:45:00Z"
            }
        ]
    },
    "change_type": "status_change"  # or priority_change, assignment_change, etc.
}
```

#### Usage:
```python
from devsync_ai.services.jira_templates import create_jira_message

# Generic factory function
message = create_jira_message(data)

# Or use specific convenience functions
from devsync_ai.services.jira_templates import (
    create_status_change_message,
    create_priority_change_message,
    create_assignment_change_message,
    create_comment_message,
    create_blocker_message,
    create_sprint_change_message
)

status_message = create_status_change_message(data)
priority_message = create_priority_change_message(data)
# etc.
```

### 4. Alert/Blocker Templates

High-visibility templates for urgent issues and critical alerts with emergency-focused formatting.

#### Available Templates:

##### Build Failure Template (`build_failure`)
- High-visibility formatting with urgent colors
- Build-specific information (branch, commit, pipeline)
- Retry and blocking actions
- CI/CD integration details

##### Deployment Issue Template (`deployment_issue`)
- Deployment context (environment, version, rollback availability)
- Health check and rollback actions
- Service impact assessment

##### Security Vulnerability Template (`security_vulnerability`)
- CVE information and CVSS scoring
- Confidentiality warnings
- Security team escalation actions
- Incident response triggers

##### Service Outage Template (`service_outage`)
- User impact metrics and affected services
- Status page integration
- War room and incident response actions

##### Critical Bug Template (`critical_bug`)
- Bug impact assessment
- Immediate action requirements
- Data integrity concerns

##### Team Blocker Template (`team_blocker`)
- Team productivity impact
- Infrastructure dependencies
- Escalation to management

##### Dependency Issue Template (`dependency_issue`)
- Third-party service dependencies
- Backup service activation
- Vendor communication

#### Data Structure:
```python
{
    "alert": {
        "id": "ALERT-001",
        "type": "build_failure",
        "severity": "high",  # critical, high, medium, low
        "title": "Production Build Failing",
        "description": "Main branch build failing due to test failures",
        "affected_systems": ["CI/CD", "Production Deployment"],
        "impact": "Blocks all deployments",
        "created_at": "2025-08-12T16:00:00Z",
        "assigned_to": "devops-team",
        "escalation_contacts": ["alice@company.com", "bob@company.com"],
        "sla_breach_time": "2025-08-12T18:00:00Z",
        "resolution_steps": [
            "Check test failures in CI logs",
            "Fix failing tests",
            "Re-run pipeline"
        ],
        "related_pr": 456,
        "related_tickets": ["DP-789"]
    }
}
```

#### Usage:
```python
from devsync_ai.services.alert_templates import create_alert_message

# Generic factory function
message = create_alert_message(data)

# Or use specific convenience functions
from devsync_ai.services.alert_templates import (
    create_build_failure_alert,
    create_deployment_issue_alert,
    create_security_vulnerability_alert,
    create_service_outage_alert,
    create_critical_bug_alert,
    create_team_blocker_alert,
    create_dependency_issue_alert
)

build_alert = create_build_failure_alert(data)
security_alert = create_security_vulnerability_alert(data)
# etc.
```

## Visual Elements

### Status Indicators
- 🟢 Active/Success/Low Priority
- 🟡 Warning/Attention needed/Medium Priority
- 🔴 Blocked/Error/High Priority
- ⚪ Inactive/Unknown/Lowest Priority
- ✅ Completed/Approved/Done
- ⏳ Pending/In progress
- ❌ Failed/Rejected/Cancelled
- 🚨 Blocker/Critical Priority
- 📋 To Do/Backlog
- 👀 In Review/Code Review
- 🧪 Testing/QA
- 🚫 Blocked Status

### Progress Bars
Text-based progress visualization:
```
████████░░ 8/10 (80%)
```

### Interactive Buttons
- **Primary Actions**: Merge, Approve, Review, Start Work, Mark Done, Take Ownership (styled in blue)
- **Secondary Actions**: View, Comment, Assign, Add to Queue, Add Update
- **Destructive Actions**: Close, Delete, Escalate, Rollback (styled in red when appropriate)
- **JIRA Actions**: View Ticket, Add Comment, Start Work, Resume Work, Escalate Blocker
- **Alert Actions**: Escalate Now, Take Ownership, Retry Build, Rollback, Start War Room, Block Deployments

## Integration Examples

### Basic Integration
```python
from devsync_ai.services.slack_templates import create_standup_message
from devsync_ai.services.pr_status_templates import create_pr_message_by_action
from devsync_ai.services.jira_templates import create_jira_message
from devsync_ai.services.alert_templates import create_alert_message
import requests

def send_to_slack(webhook_url, message):
    """Send message to Slack webhook."""
    response = requests.post(webhook_url, json=message)
    return response.status_code == 200

# Daily standup
standup_data = {...}  # Your standup data
standup_message = create_standup_message(standup_data)
send_to_slack(SLACK_WEBHOOK_URL, standup_message)

# PR notification
pr_data = {...}  # Your PR data
pr_message = create_pr_message_by_action(pr_data)
send_to_slack(SLACK_WEBHOOK_URL, pr_message)

# JIRA notification
jira_data = {...}  # Your JIRA data
jira_message = create_jira_message(jira_data)
send_to_slack(SLACK_WEBHOOK_URL, jira_message)

# Alert notification
alert_data = {...}  # Your alert data
alert_message = create_alert_message(alert_data)
send_to_slack(SLACK_WEBHOOK_URL, alert_message)
```

### Webhook Integration
```python
from flask import Flask, request
from devsync_ai.services.pr_status_templates import create_pr_message_by_action
from devsync_ai.services.jira_templates import create_jira_message

app = Flask(__name__)

@app.route('/github-webhook', methods=['POST'])
def github_webhook():
    """Handle GitHub webhook events."""
    payload = request.json
    
    if payload.get('action') in ['opened', 'closed', 'merged']:
        pr_data = {
            "pr": {
                "id": payload['pull_request']['number'],
                "title": payload['pull_request']['title'],
                "author": payload['pull_request']['user']['login'],
                # ... map other fields
            },
            "action": payload['action']
        }
        
        message = create_pr_message_by_action(pr_data)
        send_to_slack(SLACK_WEBHOOK_URL, message)
    
    return "OK"

@app.route('/jira-webhook', methods=['POST'])
def jira_webhook():
    """Handle JIRA webhook events."""
    payload = request.json
    
    if payload.get('webhookEvent') == 'jira:issue_updated':
        # Determine change type from changelog
        change_type = 'updated'
        changelog = payload.get('changelog', {})
        
        for item in changelog.get('items', []):
            if item['field'] == 'status':
                change_type = 'status_change'
            elif item['field'] == 'priority':
                change_type = 'priority_change'
            elif item['field'] == 'assignee':
                change_type = 'assignment_change'
        
        issue = payload['issue']
        jira_data = {
            "ticket": {
                "key": issue['key'],
                "summary": issue['fields']['summary'],
                "assignee": issue['fields'].get('assignee', {}).get('displayName', 'Unassigned'),
                # ... map other fields
            },
            "change_type": change_type
        }
        
        message = create_jira_message(jira_data)
        send_to_slack(SLACK_WEBHOOK_URL, message)
    
    return "OK"
```

## Customization

### Team-Specific Styling
```python
# Custom team colors and emojis
TEAM_CONFIGS = {
    "frontend": {
        "emoji": "🎨",
        "color": "#FF6B6B"
    },
    "backend": {
        "emoji": "⚙️",
        "color": "#4ECDC4"
    },
    "qa": {
        "emoji": "🧪",
        "color": "#45B7D1"
    }
}

def create_custom_standup(data, team_config):
    """Create standup with team-specific styling."""
    # Modify data with team config
    data["team_emoji"] = team_config["emoji"]
    return create_standup_message(data)
```

### Custom Action Buttons
```python
def add_custom_buttons(message, custom_actions):
    """Add custom action buttons to message."""
    custom_block = {
        "type": "actions",
        "elements": custom_actions
    }
    message["blocks"].append(custom_block)
    return message
```

## Error Handling

The templates include robust error handling:

- **Missing Data**: Gracefully handles missing fields with defaults
- **Invalid Timestamps**: Skips timestamp formatting if invalid
- **Empty Arrays**: Handles empty reviewers, tickets, etc.
- **Malformed Data**: Continues processing with available data

```python
# Example of error-resistant usage
try:
    message = create_pr_message_by_action(potentially_incomplete_data)
    send_to_slack(webhook_url, message)
except Exception as e:
    logger.error(f"Failed to create PR message: {e}")
    # Send fallback notification
    fallback_message = {
        "text": f"PR #{pr_id} was {action}",
        "blocks": [...]
    }
    send_to_slack(webhook_url, fallback_message)
```

## Testing

### Unit Tests
```bash
# Run template tests
python3 test_templates_simple.py

# Run with pytest (if available)
pytest tests/test_slack_templates.py -v
```

### Manual Testing
```python
# Test with example data
from examples.slack_template_examples import *

# Generate all example messages
example_daily_standup()
example_new_pr()
example_pr_ready_for_review()
# ... etc
```

## Performance Considerations

- **Message Size**: Slack has limits on message size and block count
- **Rate Limiting**: Respect Slack API rate limits
- **Batch Processing**: Group related notifications when possible

```python
# Batch multiple PR updates
def send_batch_pr_updates(pr_updates):
    """Send multiple PR updates in a single message."""
    if len(pr_updates) > 5:
        # Send summary instead of individual messages
        summary = create_pr_batch_summary(pr_updates)
        send_to_slack(webhook_url, summary)
    else:
        for pr_data in pr_updates:
            message = create_pr_message_by_action(pr_data)
            send_to_slack(webhook_url, message)
```

## Best Practices

1. **Consistent Timing**: Send standups at the same time daily
2. **Relevant Notifications**: Filter notifications by team/project relevance
3. **Action Buttons**: Only include actionable buttons for the target audience
4. **Thread Responses**: Use threading for follow-up messages
5. **Fallback Text**: Always provide meaningful fallback text for accessibility

## Troubleshooting

### Common Issues

**Templates not rendering properly:**
- Check Slack Block Kit validator
- Verify JSON structure
- Ensure all required fields are present

**Missing interactive elements:**
- Verify Slack app has necessary permissions
- Check button action IDs are unique
- Ensure webhook URLs are accessible

**Performance issues:**
- Reduce message complexity
- Batch similar notifications
- Cache template generation results

### Debug Mode
```python
import json

# Pretty print message for debugging
message = create_standup_message(data)
print(json.dumps(message, indent=2))

# Validate with Slack Block Kit Builder
# https://app.slack.com/block-kit-builder
```

## Future Enhancements

- **Threaded Conversations**: Automatic threading for related updates
- **User Mentions**: Smart @mentions based on PR assignments
- **Custom Themes**: Team-specific color schemes and branding
- **Analytics Integration**: Usage metrics and engagement tracking
- **Multi-language Support**: Internationalization for global teams