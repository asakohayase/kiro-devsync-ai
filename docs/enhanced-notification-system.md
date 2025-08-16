# Enhanced Notification System

The Enhanced Notification System is a comprehensive, intelligent notification management system for DevSync AI that provides advanced filtering, routing, batching, deduplication, and scheduling capabilities.

## Features

### 🎯 Intelligent Channel Routing
- **Smart routing** based on notification type, urgency, and content
- **Team-specific channels** with customizable mappings
- **Urgency-based overrides** for critical notifications
- **Fallback routing** to ensure no notifications are lost

### 🚫 Duplicate Prevention
- **Content-based deduplication** using configurable strategies
- **Time-window filtering** to prevent spam
- **Database-backed storage** for persistent deduplication
- **Automatic cleanup** of old records

### ⏰ Work Hours Scheduling
- **Configurable work hours** per team
- **Timezone support** for global teams
- **Urgent bypass** for critical notifications
- **Background scheduling** for non-urgent messages

### 📦 Smart Batching
- **Intelligent batching** based on content similarity
- **Anti-spam protection** with rate limiting
- **Adaptive timing** based on activity patterns
- **Burst detection** and cooldown periods

### 🎨 Template Integration
- **Rich message templates** with the existing template factory
- **Team-specific branding** and customization
- **Accessibility support** with fallback text
- **Interactive elements** with button controls

### 📊 Analytics & Monitoring
- **Comprehensive metrics** on all system components
- **Health monitoring** with status endpoints
- **Performance tracking** and optimization
- **Database analytics** with retention policies

## Architecture

```
Enhanced Notification System
├── Channel Router
│   ├── Default routing rules
│   ├── Team-specific mappings
│   ├── Urgency analysis
│   └── Fallback handling
├── Deduplicator
│   ├── Content hashing
│   ├── Database storage
│   ├── Time-window filtering
│   └── Cleanup automation
├── Smart Batcher
│   ├── Content similarity grouping
│   ├── Anti-spam protection
│   ├── Adaptive timing
│   └── Burst detection
├── Scheduler
│   ├── Work hours enforcement
│   ├── Background processing
│   ├── Retry logic
│   └── Health monitoring
└── Integration Layer
    ├── GitHub webhooks
    ├── JIRA webhooks
    ├── Template factory
    └── Slack API
```

## Quick Start

### 1. Installation

The enhanced notification system is part of DevSync AI. Ensure you have the required dependencies:

```bash
# Install Python dependencies
uv sync

# Install optional dependencies for full functionality
uv add supabase psutil
```

### 2. Configuration

Create a configuration file based on the example:

```bash
# Create example configuration
python scripts/start_notification_system.py --create-config config/notifications.yaml

# Edit the configuration file
vim config/notifications.yaml
```

### 3. Database Setup

Run the database migration to create required tables:

```sql
-- Run the migration script
\i migrations/create_notification_tables.sql
```

### 4. Environment Variables

Set the required environment variables:

```bash
export SUPABASE_URL="your-supabase-url"
export SUPABASE_ANON_KEY="your-supabase-anon-key"
export SLACK_BOT_TOKEN="your-slack-bot-token"
export SLACK_APP_TOKEN="your-slack-app-token"
```

### 5. Start the System

```bash
# Start with default configuration
python scripts/start_notification_system.py

# Start with custom configuration
python scripts/start_notification_system.py --config config/notifications.yaml

# Run tests
python scripts/start_notification_system.py --test
```

## Configuration

### System Configuration

```yaml
system:
  enabled: true
  debug_mode: false
  analytics_enabled: true
  health_check_enabled: true
```

### Work Hours

```yaml
work_hours:
  enabled: true
  start_hour: 9
  end_hour: 17
  timezone: "UTC"
  work_days: [0, 1, 2, 3, 4]  # Monday-Friday
  urgent_bypass: true
```

### Team-Specific Settings

```yaml
teams:
  frontend_team:
    name: "Frontend Team"
    channels:
      pr_new: "#frontend-prs"
      pr_ready: "#frontend-reviews"
      jira_status: "#frontend-tickets"
    work_hours:
      start_hour: 10
      end_hour: 18
      timezone: "America/New_York"
```

## API Usage

### Sending Notifications

```python
from devsync_ai.core.notification_integration import default_notification_system

# Send GitHub notification
result = await default_notification_system.send_github_notification(
    event_type="pull_request.opened",
    payload=github_payload,
    team_id="frontend_team"
)

# Send JIRA notification
result = await default_notification_system.send_jira_notification(
    event_type="jira:issue_updated",
    payload=jira_payload,
    team_id="backend_team"
)

# Send custom notification
result = await default_notification_system.send_notification(
    notification_type="alert_build",
    event_type="alert.build_failure",
    data=alert_data,
    team_id="devops_team"
)
```

### System Management

```python
# Get system health
health = await default_notification_system.get_health_status()

# Get statistics
stats = await default_notification_system.get_system_stats()

# Flush pending batches
flushed = await default_notification_system.flush_all_batches()

# Force scheduler run
result = await default_notification_system.force_scheduler_run()
```

## Webhook Integration

The system automatically integrates with existing webhook endpoints:

### GitHub Webhooks

```python
# In webhooks/routes.py
@webhook_router.post("/github")
async def github_webhook(request: Request):
    # Enhanced notifications are automatically sent
    # for all GitHub events
```

### JIRA Webhooks

```python
# New JIRA webhook endpoint
@webhook_router.post("/jira")
async def jira_webhook(request: Request):
    # Processes JIRA events and sends notifications
```

## Health Monitoring

### Health Check Endpoints

- `GET /webhooks/health` - Overall system health
- `GET /webhooks/notifications/health` - Detailed notification system health
- `GET /webhooks/notifications/stats` - System statistics

### Manual Operations

- `POST /webhooks/notifications/flush` - Flush pending batches
- `POST /webhooks/notifications/scheduler/run` - Force scheduler run

## Database Schema

The system uses several database tables:

### notification_log
Stores notification records for duplicate prevention.

### scheduled_notifications
Stores notifications scheduled for later delivery.

### notification_analytics
Stores analytics data for monitoring and optimization.

### channel_routing_stats
Stores channel routing statistics.

### batch_processing_stats
Stores batch processing performance data.

## Monitoring & Analytics

### Key Metrics

- **Processing Rate**: Notifications processed per minute
- **Duplicate Rate**: Percentage of notifications filtered as duplicates
- **Batch Efficiency**: Average batch size and processing time
- **Channel Distribution**: Messages per channel
- **Error Rate**: Failed notifications and processing errors

### Performance Monitoring

```python
# Get comprehensive statistics
stats = await system.get_system_stats()

# Monitor specific components
router_stats = system.router.get_routing_stats()
dedup_stats = system.deduplicator.get_deduplication_stats()
batch_stats = system.batcher.get_batch_stats()
```

## Troubleshooting

### Common Issues

1. **System Not Starting**
   - Check configuration file syntax
   - Verify environment variables
   - Check database connectivity

2. **Notifications Not Sending**
   - Verify Slack token permissions
   - Check channel routing rules
   - Review filtering configuration

3. **High Memory Usage**
   - Run cleanup operations
   - Adjust cache settings
   - Check for memory leaks in logs

4. **Performance Issues**
   - Monitor batch processing times
   - Check database query performance
   - Review spam prevention settings

### Debug Mode

Enable debug mode for detailed logging:

```yaml
system:
  debug_mode: true
```

### Log Analysis

```bash
# View system logs
tail -f notification_system.log

# Search for errors
grep "ERROR" notification_system.log

# Monitor performance
grep "processing_time_ms" notification_system.log
```

## Testing

### Unit Tests

```bash
# Run all tests
uv run pytest tests/test_enhanced_notification_system.py -v

# Run specific test categories
uv run pytest tests/test_enhanced_notification_system.py::TestChannelRouter -v
uv run pytest tests/test_enhanced_notification_system.py::TestNotificationDeduplicator -v
```

### Integration Tests

```bash
# Test with real system
python scripts/start_notification_system.py --test

# Performance tests
uv run pytest tests/test_enhanced_notification_system.py::TestPerformanceAndLoad -v
```

### Manual Testing

```bash
# Send test notification via API
curl -X POST http://localhost:8000/webhooks/notifications/test \
  -H "Content-Type: application/json" \
  -d '{"type": "pr_new", "data": {"number": 123}}'
```

## Best Practices

### Configuration

1. **Start Simple**: Begin with default settings and customize gradually
2. **Team Isolation**: Use team-specific configurations for different workflows
3. **Monitor Performance**: Regularly check system metrics and adjust settings
4. **Test Changes**: Validate configuration changes in a test environment

### Operations

1. **Regular Cleanup**: Schedule periodic cleanup of old data
2. **Health Monitoring**: Set up alerts for system health issues
3. **Capacity Planning**: Monitor growth and scale resources accordingly
4. **Backup Strategy**: Ensure database backups include notification data

### Development

1. **Use Type Hints**: All code uses comprehensive type annotations
2. **Error Handling**: Graceful error handling with proper logging
3. **Testing**: Comprehensive test coverage for all components
4. **Documentation**: Keep configuration and code documentation updated

## Migration Guide

### From Legacy System

1. **Backup Current Configuration**: Save existing Slack notification settings
2. **Install Dependencies**: Add required packages for enhanced system
3. **Run Database Migration**: Create new tables for enhanced features
4. **Update Configuration**: Convert settings to new format
5. **Test Thoroughly**: Validate all notification types work correctly
6. **Monitor Transition**: Watch for issues during initial deployment

### Rollback Plan

If issues occur, you can disable the enhanced system:

```yaml
system:
  enabled: false
```

This will fall back to the legacy notification system while you troubleshoot.

## Support

### Getting Help

1. **Check Logs**: Review system logs for error messages
2. **Health Endpoints**: Use health check endpoints to diagnose issues
3. **Configuration Validation**: Validate your configuration file
4. **Test Mode**: Run system tests to identify problems

### Contributing

1. **Follow Code Standards**: Use type hints and comprehensive documentation
2. **Add Tests**: Include tests for new features
3. **Update Documentation**: Keep docs current with changes
4. **Performance Considerations**: Monitor impact of changes on system performance

## Changelog

### Version 1.0.0
- Initial release of enhanced notification system
- Channel routing with team-specific mappings
- Duplicate prevention with database storage
- Work hours scheduling with timezone support
- Smart batching with anti-spam protection
- Template integration with existing factory
- Comprehensive analytics and monitoring
- Full webhook integration
- Complete test suite and documentation