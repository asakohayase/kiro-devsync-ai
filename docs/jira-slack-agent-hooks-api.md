# JIRA Slack Agent Hooks API Documentation

## Overview

The JIRA Slack Agent Hooks system provides automated, intelligent Slack notifications in response to JIRA webhook events. This system integrates seamlessly with the existing DevSync AI infrastructure to deliver contextual, team-specific notifications.

## Core Components

### Agent Hook Base Class

All agent hooks extend the base `AgentHook` class:

```python
from devsync_ai.core.agent_hooks import AgentHook, EnrichedEvent, HookExecutionResult

class CustomHook(AgentHook):
    async def execute(self, event: EnrichedEvent) -> HookExecutionResult:
        """Execute the hook logic for the given event."""
        pass
    
    def should_execute(self, event: EnrichedEvent) -> bool:
        """Determine if this hook should execute for the given event."""
        return True
```

### Event Processing Pipeline

The system processes JIRA webhook events through a standardized pipeline:

1. **Webhook Reception** - JIRA webhooks received via `/webhooks/jira`
2. **Event Processing** - Raw webhook data parsed and enriched
3. **Event Classification** - Events categorized by type, urgency, and significance
4. **Rule Evaluation** - Team-specific rules applied to determine hook execution
5. **Hook Execution** - Appropriate hooks executed based on event classification
6. **Notification Generation** - Slack messages formatted and sent

## API Endpoints

### Hook Management

#### GET /api/hooks/status
Get overall hook system status and health metrics.

**Response:**
```json
{
  "status": "healthy",
  "active_hooks": 12,
  "total_executions_today": 45,
  "success_rate": 98.5,
  "average_execution_time_ms": 150
}
```

#### GET /api/hooks/configurations/{team_id}
Get hook configuration for a specific team.

**Parameters:**
- `team_id` (string): Team identifier

**Response:**
```json
{
  "team_id": "engineering",
  "enabled_hooks": ["status_change", "assignment", "comment"],
  "configurations": {
    "status_change": {
      "enabled": true,
      "channels": ["#dev-updates"],
      "conditions": [
        {
          "field": "priority",
          "operator": "in",
          "values": ["High", "Critical"]
        }
      ]
    }
  }
}
```

#### PUT /api/hooks/configurations/{team_id}
Update hook configuration for a team.

**Request Body:**
```json
{
  "configurations": {
    "status_change": {
      "enabled": true,
      "channels": ["#dev-updates", "#alerts"],
      "conditions": [
        {
          "field": "priority",
          "operator": "in",
          "values": ["High", "Critical"]
        }
      ]
    }
  }
}
```

#### GET /api/hooks/executions
Get hook execution history with filtering options.

**Query Parameters:**
- `team_id` (optional): Filter by team
- `hook_type` (optional): Filter by hook type
- `start_date` (optional): Start date for filtering
- `end_date` (optional): End date for filtering
- `limit` (optional): Number of results (default: 50)

**Response:**
```json
{
  "executions": [
    {
      "execution_id": "exec_123",
      "hook_type": "status_change",
      "team_id": "engineering",
      "ticket_key": "PROJ-123",
      "success": true,
      "execution_time_ms": 145,
      "notification_sent": true,
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1,
  "has_more": false
}
```

### Analytics and Monitoring

#### GET /api/hooks/analytics/performance
Get performance analytics for hook executions.

**Query Parameters:**
- `time_range` (optional): "1h", "24h", "7d", "30d" (default: "24h")
- `team_id` (optional): Filter by team
- `hook_type` (optional): Filter by hook type

**Response:**
```json
{
  "time_range": "24h",
  "total_executions": 156,
  "success_rate": 98.7,
  "average_execution_time_ms": 142,
  "error_rate": 1.3,
  "performance_trend": "stable",
  "hook_type_breakdown": {
    "status_change": 89,
    "assignment": 34,
    "comment": 23,
    "blocker": 10
  }
}
```

#### GET /api/hooks/analytics/team-metrics/{team_id}
Get team-specific hook analytics.

**Response:**
```json
{
  "team_id": "engineering",
  "active_hooks": 4,
  "notifications_sent_today": 23,
  "most_active_hook": "status_change",
  "workload_distribution": {
    "john.doe": 8,
    "jane.smith": 12,
    "bob.wilson": 6
  },
  "response_times": {
    "average_ms": 134,
    "p95_ms": 245,
    "p99_ms": 456
  }
}
```

## Hook Types

### StatusChangeHook

Triggers when JIRA ticket status changes.

**Configuration Options:**
```yaml
status_change:
  enabled: true
  channels: ["#dev-updates"]
  conditions:
    - field: "priority"
      operator: "in"
      values: ["High", "Critical"]
  urgency_mapping:
    "To Do -> In Progress": "low"
    "In Progress -> Blocked": "high"
    "In Review -> Done": "medium"
```

**Event Data:**
- `old_status`: Previous ticket status
- `new_status`: New ticket status
- `ticket_details`: Full ticket information
- `assignee`: Current assignee information

### AssignmentHook

Triggers when tickets are assigned or reassigned.

**Configuration Options:**
```yaml
assignment:
  enabled: true
  channels: ["#team-assignments"]
  workload_warnings: true
  max_tickets_per_assignee: 5
  conditions:
    - field: "project"
      operator: "equals"
      value: "MYPROJECT"
```

**Event Data:**
- `assignee`: New assignee information
- `previous_assignee`: Previous assignee (if reassignment)
- `workload_analysis`: Current workload metrics
- `ticket_details`: Full ticket information

### CommentHook

Triggers when comments are added to high-priority tickets.

**Configuration Options:**
```yaml
comment:
  enabled: true
  channels: ["#ticket-discussions"]
  conditions:
    - field: "ticket_priority"
      operator: "in"
      values: ["High", "Critical"]
  keyword_filters:
    - "blocker"
    - "urgent"
    - "production"
```

**Event Data:**
- `comment_author`: Comment author information
- `comment_content`: Comment text (truncated)
- `ticket_details`: Full ticket information
- `significance_level`: Calculated comment significance

### BlockerHook

Triggers when tickets are marked as blocked or contain blocker keywords.

**Configuration Options:**
```yaml
blocker:
  enabled: true
  channels: ["#blockers", "#dev-alerts"]
  escalation_enabled: true
  escalation_delay_minutes: 30
  conditions:
    - field: "status"
      operator: "equals"
      value: "Blocked"
```

**Event Data:**
- `blocker_type`: Type of blocker detected
- `blocker_description`: Description of the blocking issue
- `affected_tickets`: Related tickets that may be impacted
- `escalation_required`: Whether escalation is needed

## Event Classification

### Event Categories

- `STATUS_CHANGE`: Ticket status transitions
- `ASSIGNMENT`: Ticket assignment changes
- `COMMENT`: New comments added
- `PRIORITY_CHANGE`: Priority level changes
- `BLOCKER`: Blocked ticket detection
- `CREATION`: New ticket creation
- `TRANSITION`: Workflow transitions

### Urgency Levels

- `LOW`: Routine updates, minor changes
- `MEDIUM`: Standard priority changes
- `HIGH`: Important updates requiring attention
- `CRITICAL`: Urgent issues requiring immediate action

### Significance Levels

- `MINOR`: Small changes with minimal impact
- `MODERATE`: Standard changes affecting workflow
- `MAJOR`: Important changes affecting multiple stakeholders
- `CRITICAL`: High-impact changes requiring immediate attention

## Error Handling

### Error Categories

1. **Webhook Processing Errors**
   - Invalid payload format
   - Authentication failures
   - Rate limiting

2. **Hook Execution Errors**
   - Rule evaluation failures
   - Template rendering errors
   - Notification delivery failures

3. **Configuration Errors**
   - Invalid rule syntax
   - Missing team configurations
   - Channel access issues

### Retry Mechanisms

The system implements exponential backoff retry logic:

- **Initial Delay**: 1 second
- **Maximum Retries**: 3 attempts
- **Backoff Multiplier**: 2x
- **Maximum Delay**: 30 seconds

### Circuit Breaker

Circuit breaker pattern prevents cascading failures:

- **Failure Threshold**: 10 consecutive failures
- **Recovery Timeout**: 60 seconds
- **Half-Open State**: Single test request before full recovery

## Security

### Authentication

- **Webhook Signatures**: JIRA webhook signatures validated using HMAC-SHA256
- **API Authentication**: Bearer token authentication for API endpoints
- **Team Access Control**: Role-based access to team configurations

### Data Privacy

- **PII Sanitization**: Personal information sanitized in notifications
- **Data Retention**: Hook execution logs retained for 90 days
- **Audit Logging**: All configuration changes logged with user attribution

## Performance Considerations

### Optimization Guidelines

1. **Async Processing**: All hook operations are asynchronous
2. **Connection Pooling**: Database and HTTP connections pooled
3. **Caching**: Frequently accessed data cached (team configs, user info)
4. **Batching**: Multiple notifications batched when possible

### Resource Limits

- **Execution Timeout**: 30 seconds per hook execution
- **Concurrent Executions**: Maximum 10 concurrent hook executions
- **Memory Limit**: 512MB per hook execution process
- **Rate Limiting**: 100 webhook events per minute per team

## Monitoring and Observability

### Health Checks

- **System Health**: `/health/hooks` endpoint
- **Individual Hook Health**: Per-hook status monitoring
- **Dependency Health**: External service connectivity checks

### Metrics Collection

- **Execution Metrics**: Success rates, latency, throughput
- **Error Metrics**: Error rates by type and category
- **Business Metrics**: Team productivity, notification effectiveness

### Alerting

- **Performance Degradation**: Slow execution times
- **High Error Rates**: Excessive failures
- **Configuration Issues**: Invalid configurations
- **Service Dependencies**: External service failures

## Integration Points

### Existing Components

- **JIRA Service**: Leverages existing JIRA API integration
- **Slack Service**: Uses existing Slack API client
- **Enhanced Notification Handler**: Integrates with notification routing
- **Template System**: Uses existing message template factory

### Database Schema

The system extends the existing database with hook-specific tables:

- `hook_executions`: Hook execution logs and results
- `team_hook_configurations`: Team-specific hook configurations
- `hook_performance_metrics`: Performance and analytics data

### Configuration Files

- `config/team_*_hooks.yaml`: Team-specific hook configurations
- `config/jira_webhook_config.example.yaml`: JIRA webhook configuration
- `config/analytics_config.example.yaml`: Analytics configuration