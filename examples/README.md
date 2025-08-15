# Slack Message Templates - Usage Examples

This directory contains comprehensive examples demonstrating how to use the Slack Message Templates system.

## Files Overview

### Core Examples
- **`comprehensive_template_usage_examples.py`** - Complete examples for all template types
- **`template_factory_usage_guide.py`** - Guide for using the template factory
- **`team_configuration_examples.py`** - Team-specific configuration examples
- **`integration_examples.py`** - Integration with external services

### Quick Start

```python
from devsync_ai.templates.standup_template import StandupTemplate
from devsync_ai.core.message_formatter import TemplateConfig

# Create configuration
config = TemplateConfig(
    team_id="my_team",
    branding={"team_name": "My Team", "logo_emoji": "🚀"},
    interactive_elements=True
)

# Create template
template = StandupTemplate(config=config)

# Format message
data = {
    "date": "2025-08-14",
    "team": "My Team",
    "team_members": [
        {
            "name": "Alice",
            "yesterday": ["Completed task A"],
            "today": ["Working on task B"],
            "blockers": []
        }
    ]
}

message = template.format_message(data)
print(f"Generated message with {len(message.blocks)} blocks")
```

## Template Types

### 1. Standup Templates
Used for daily standup summaries and team status updates.

**Data Structure:**
```python
{
    "date": "2025-08-14",
    "team": "Team Name",
    "team_members": [
        {
            "name": "Member Name",
            "status": "active|away|blocked",
            "yesterday": ["Task 1", "Task 2"],
            "today": ["Task 3", "Task 4"],
            "blockers": ["Blocker 1"]
        }
    ],
    "stats": {
        "prs_merged": 5,
        "prs_open": 3,
        "tickets_completed": 8,
        "commits": 25
    },
    "action_items": [
        {
            "description": "Action description",
            "assignee": "Person",
            "due_date": "2025-08-15"
        }
    ]
}
```

### 2. PR Templates
Used for pull request notifications and status updates.

**Data Structure:**
```python
{
    "pr": {
        "number": 123,
        "title": "PR Title",
        "description": "PR Description",
        "author": "username",
        "url": "https://github.com/repo/pull/123",
        "reviewers": ["reviewer1", "reviewer2"],
        "status": "open|closed|merged",
        "files_changed": 5,
        "additions": 100,
        "deletions": 20
    },
    "action": "opened|closed|merged|approved"
}
```

### 3. JIRA Templates
Used for JIRA ticket notifications and updates.

**Data Structure:**
```python
{
    "ticket": {
        "key": "PROJ-123",
        "summary": "Ticket Summary",
        "description": "Ticket Description",
        "priority": "High|Medium|Low",
        "status": "To Do|In Progress|Done",
        "assignee": "username",
        "url": "https://jira.company.com/browse/PROJ-123"
    },
    "change_type": "status_change|priority_change|comment_added",
    "changed_by": "username"
}
```

### 4. Alert Templates
Used for system alerts and notifications.

**Data Structure:**
```python
{
    "alert": {
        "id": "ALERT-123",
        "type": "build_failure|deployment_issue|service_outage",
        "severity": "critical|high|medium|low",
        "title": "Alert Title",
        "description": "Alert Description",
        "created_at": "2025-08-14T10:00:00Z",
        "affected_systems": ["system1", "system2"]
    }
}
```

## Configuration Options

### Basic Configuration
```python
config = TemplateConfig(
    team_id="team_name",
    branding={
        "team_name": "Display Name",
        "logo_emoji": "🚀",
        "primary_color": "#2E86AB"
    },
    interactive_elements=True,
    accessibility_mode=False
)
```

### Team-Specific Configuration
```python
# Engineering Team
engineering_config = TemplateConfig(
    team_id="engineering",
    branding={
        "team_name": "⚙️ Engineering Team",
        "logo_emoji": "⚙️",
        "primary_color": "#2E86AB"
    },
    emoji_set={
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
        "in_progress": "🔄"
    },
    interactive_elements=True,
    caching_enabled=True
)

# Design Team
design_config = TemplateConfig(
    team_id="design",
    branding={
        "team_name": "🎨 Design Team",
        "logo_emoji": "🎨",
        "primary_color": "#FF6B35"
    },
    emoji_set={
        "success": "🎉",
        "warning": "⚡",
        "error": "🚨",
        "in_progress": "🎯"
    },
    interactive_elements=True
)
```

### Accessibility Configuration
```python
accessible_config = TemplateConfig(
    team_id="accessible_team",
    accessibility_mode=True,
    interactive_elements=False,
    emoji_set={
        "success": "[SUCCESS]",
        "warning": "[WARNING]",
        "error": "[ERROR]",
        "info": "[INFO]"
    },
    fallback_text_detailed=True
)
```

## Error Handling

The templates include robust error handling:

```python
# Handle missing data
incomplete_data = {}  # Missing required fields
message = template.format_message(incomplete_data)
# Returns fallback message with graceful degradation

# Handle malformed data
malformed_data = {
    "date": 123,  # Should be string
    "team": ["not", "string"],  # Should be string
    "team_members": "not a list"  # Should be list
}
message = template.format_message(malformed_data)
# Returns message with corrected/default values
```

## Performance Considerations

### Caching
```python
config = TemplateConfig(
    team_id="performance_team",
    caching_enabled=True,
    cache_ttl=3600  # 1 hour
)
```

### Batch Processing
```python
# Process multiple messages efficiently
batch_data = [data1, data2, data3]
messages = []

for data in batch_data:
    message = template.format_message(data)
    messages.append(message)
```

## Integration Examples

### GitHub Webhook Integration
```python
def process_github_webhook(webhook_data):
    if webhook_data.get("action") == "opened":
        template = NewPRTemplate(config=config)
        data = transform_github_data(webhook_data)
        return template.format_message(data)
```

### JIRA Webhook Integration
```python
def process_jira_webhook(webhook_data):
    change_type = determine_change_type(webhook_data)
    template = get_jira_template(change_type)
    data = transform_jira_data(webhook_data)
    return template.format_message(data)
```

## Testing

### Unit Testing
```python
def test_standup_template():
    template = StandupTemplate()
    data = create_test_data()
    message = template.format_message(data)
    
    assert len(message.blocks) > 0
    assert message.text is not None
    assert "Daily Standup" in message.text
```

### Integration Testing
```python
def test_end_to_end_flow():
    # Test complete flow from webhook to Slack message
    webhook_data = create_mock_webhook()
    message = process_webhook(webhook_data)
    response = send_to_slack(message)
    
    assert response["ok"] is True
```

## Best Practices

1. **Always provide fallback text** for accessibility
2. **Use appropriate emoji sets** for your team culture
3. **Enable caching** for production environments
4. **Handle errors gracefully** with meaningful fallbacks
5. **Test with edge cases** including malformed data
6. **Configure team-specific branding** for better engagement
7. **Use batch processing** for high-volume scenarios
8. **Monitor performance** and adjust cache settings as needed

## Troubleshooting

### Common Issues

1. **Template not rendering**: Check data structure matches expected format
2. **Missing blocks**: Verify all required fields are present
3. **Performance issues**: Enable caching and use batch processing
4. **Accessibility problems**: Enable accessibility mode and detailed fallbacks

### Debug Mode
```python
config = TemplateConfig(
    team_id="debug_team",
    debug_mode=True,
    performance_logging=True
)
```

## Support

For additional help:
1. Check the comprehensive examples in this directory
2. Review the test files for usage patterns
3. Examine the template source code for implementation details
4. Use the performance benchmarks for optimization guidance