# JIRA Webhook Agent Hooks System

## Overview

The JIRA Webhook Agent Hooks system provides intelligent, event-driven automation that responds to JIRA webhook events and triggers contextual Slack notifications. This system leverages Agent Hook capabilities to provide sophisticated event processing, intelligent routing, and seamless integration with the existing enhanced notification system.

## Architecture

### High-Level Components

```mermaid
graph TB
    A[JIRA Webhook Events] --> B[Agent Hook Dispatcher]
    B --> C[Hook Event Processor]
    C --> D[Event Classification Engine]
    D --> E[Hook Rule Engine]
    E --> F[Specialized Agent Hooks]
    F --> G[Enhanced Notification Handler]
    G --> H[Slack Service]
    
    I[Hook Configuration Manager] --> E
    J[Hook Analytics Engine] --> K[Hook Monitoring Dashboard]
    C --> J
```

### Core Components

1. **Agent Hook Dispatcher**: Central dispatcher that receives JIRA webhook events and routes them to appropriate Agent Hooks
2. **Event Processors**: Specialized processors for different JIRA event types (status changes, assignments, comments)
3. **Agent Hooks**: Event-driven automation components that process specific types of JIRA events
4. **Security Validator**: Handles webhook signature verification and payload validation
5. **Rate Limiter**: Prevents abuse and manages webhook request rates
6. **Analytics Engine**: Tracks performance metrics and system health

## Agent Hook Types

### StatusChangeHook
- **Purpose**: Processes JIRA ticket status transitions
- **Triggers**: Status changes (To Do → In Progress → Done)
- **Features**:
  - Analyzes status change significance
  - Routes to appropriate Slack channels based on status and priority
  - Includes sprint context and assignee information
  - Detects blocking status transitions

### BlockerDetectionHook
- **Purpose**: Identifies and alerts on blocking issues
- **Triggers**: Tickets moving to blocking statuses or remaining stagnant
- **Features**:
  - Immediately alerts relevant team members and managers
  - Escalates based on blocker severity and duration
  - Creates actionable Slack messages with resolution suggestions
  - Tracks blocker resolution time

### AssignmentChangeHook
- **Purpose**: Handles ticket assignment and reassignment events
- **Triggers**: When tickets are assigned/reassigned to team members
- **Features**:
  - Notifies assignees with ticket context and priority
  - Updates team workload visibility in designated channels
  - Includes estimated effort and deadline information
  - Warns about workload overallocation

### CommentAddedHook
- **Purpose**: Processes new JIRA comments for tracked tickets
- **Triggers**: New comments on JIRA tickets
- **Features**:
  - Filters for significant comments (mentions, decisions, blockers)
  - Creates threaded Slack discussions linked to JIRA
  - Maintains comment history and context
  - Detects urgency and decision keywords

### PriorityChangeHook
- **Purpose**: Handles ticket priority escalations and changes
- **Triggers**: When ticket priority is escalated or changed
- **Features**:
  - Immediately notifies affected team members
  - Routes high/critical priority changes to management channels
  - Includes justification and impact analysis
  - Tracks priority change patterns

## Event Processing Pipeline

### 1. Webhook Reception
```python
POST /webhooks/jira/events
```
- Validates JIRA webhook signatures
- Parses webhook payload
- Applies rate limiting
- Logs webhook events

### 2. Event Processing
- **IssueUpdatedProcessor**: Handles issue updates and field changes
- **IssueTransitionProcessor**: Processes workflow transitions
- **IssueAssignedProcessor**: Manages assignment events
- **CommentAddedProcessor**: Analyzes comment content

### 3. Event Classification
- Determines event category (status_change, assignment, comment, etc.)
- Analyzes urgency level (low, medium, high, critical)
- Assesses significance (minor, moderate, major, critical)
- Identifies affected teams and stakeholders

### 4. Hook Execution
- Routes events to applicable Agent Hooks
- Applies team-specific rules and conditions
- Executes hooks with timeout and retry logic
- Collects execution results and metrics

### 5. Notification Delivery
- Integrates with Enhanced Notification Handler
- Uses SlackMessageFormatterFactory for rich formatting
- Applies batching and scheduling rules
- Delivers notifications to appropriate channels

## Configuration

### Team Configuration Example
```yaml
teams:
  backend-team:
    status_change:
      enabled: true
      channels: ["#backend-updates"]
      conditions:
        - field: "component"
          operator: "contains"
          values: ["API", "Database"]
      urgency_mapping:
        "In Progress -> Blocked": "critical"
        
    assignment:
      enabled: true
      channels: ["#backend-assignments"]
      max_tickets_per_assignee: 3
      workload_warnings: true
```

### Hook Conditions
Hooks support complex conditional logic:
- **Field Conditions**: Match specific field values
- **Priority Filters**: Filter by ticket priority
- **Component Filters**: Filter by project components
- **Time-based Rules**: Work hours, frequency limits
- **Stakeholder Rules**: Team member and role-based routing

## API Endpoints

### Webhook Endpoints
- `POST /webhooks/jira/events` - Main JIRA webhook endpoint
- `GET /webhooks/jira/health` - System health check
- `GET /webhooks/jira/metrics` - Performance metrics
- `POST /webhooks/jira/simulate` - Test webhook processing

### Hook Management
- `GET /webhooks/jira/hooks` - List active hooks
- `POST /webhooks/jira/hooks/{hook_id}/enable` - Enable hook
- `POST /webhooks/jira/hooks/{hook_id}/disable` - Disable hook
- `GET /webhooks/jira/hooks/{hook_id}/stats` - Hook statistics

## Security Features

### Webhook Security
- **Signature Verification**: Validates JIRA webhook signatures using HMAC-SHA256
- **Rate Limiting**: Prevents abuse with configurable request limits
- **IP Filtering**: Optional IP allowlist for webhook sources
- **Payload Validation**: Comprehensive validation of webhook structure

### Access Control
- **Team-based Access**: Hooks only access authorized team data
- **Channel Permissions**: Verifies Slack channel access rights
- **Configuration Security**: Protects sensitive team configurations
- **Audit Logging**: Tracks configuration changes and access patterns

## Monitoring and Analytics

### Metrics Tracked
- Hook execution frequency and success rates
- Processing latency and performance trends
- Error rates and failure patterns
- Notification delivery success rates
- Team engagement metrics

### Health Monitoring
- **System Health**: Overall system status and component health
- **Hook Health**: Individual hook performance and status
- **Integration Health**: External service connectivity
- **Configuration Health**: Rule and configuration validity

### Alerting
- **Performance Degradation**: Slow hook execution times
- **High Error Rates**: Excessive failures
- **Configuration Issues**: Invalid or missing configurations
- **Service Dependencies**: JIRA or Slack service issues

## Error Handling

### Error Categories
1. **Webhook Processing Errors**: Malformed payloads, authentication failures
2. **Hook Execution Errors**: Rule evaluation failures, template rendering errors
3. **Configuration Errors**: Invalid rule syntax, missing configurations

### Recovery Mechanisms
- **Exponential Backoff**: For transient failures
- **Circuit Breaker**: For persistent service failures
- **Fallback Templates**: When custom templates fail
- **Dead Letter Queue**: For failed webhook processing
- **Error Notifications**: Alert administrators of critical failures

## Installation and Setup

### 1. Environment Variables
```bash
# Required
JIRA_WEBHOOK_SECRET=your-webhook-secret
SLACK_BOT_TOKEN=xoxb-your-slack-token
DATABASE_URL=postgresql://user:pass@localhost/db

# Optional
JIRA_WEBHOOK_RATE_LIMIT=100
HOOK_EXECUTION_TIMEOUT=30
```

### 2. Database Setup
```sql
-- Hook execution logs
CREATE TABLE hook_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hook_id VARCHAR(255) NOT NULL,
    execution_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    team_id VARCHAR(100) NOT NULL,
    ticket_key VARCHAR(50),
    success BOOLEAN NOT NULL,
    execution_time_ms INTEGER NOT NULL,
    notification_sent BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

-- Team hook configurations
CREATE TABLE team_hook_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id VARCHAR(100) NOT NULL,
    hook_type VARCHAR(100) NOT NULL,
    configuration JSONB NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(team_id, hook_type)
);
```

### 3. JIRA Webhook Configuration
1. Go to JIRA Administration → System → Webhooks
2. Create new webhook with URL: `https://your-domain.com/webhooks/jira/events`
3. Select events: Issue Created, Updated, Deleted, Assigned, Commented
4. Set webhook secret for security
5. Test webhook connection

### 4. Start the System
```bash
# Using the startup script
python scripts/start_jira_webhook_system.py

# Or integrate with your FastAPI application
from devsync_ai.webhooks.jira_webhook_handler import initialize_dispatcher

# In your startup event
await initialize_dispatcher()
```

## Usage Examples

### Testing Webhook Processing
```bash
# Test with sample payload
curl -X POST http://localhost:8000/webhooks/jira/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "webhookEvent": "jira:issue_updated",
    "issue": {
      "key": "TEST-123",
      "fields": {
        "summary": "Test issue",
        "status": {"name": "In Progress"},
        "priority": {"name": "High"}
      }
    }
  }'
```

### Monitoring System Health
```bash
# Check system health
curl http://localhost:8000/webhooks/jira/health

# Get performance metrics
curl http://localhost:8000/webhooks/jira/metrics

# List active hooks
curl http://localhost:8000/webhooks/jira/hooks
```

## Troubleshooting

### Common Issues

1. **Webhook Not Receiving Events**
   - Check JIRA webhook configuration
   - Verify webhook URL is accessible
   - Check firewall and network settings

2. **Signature Verification Failures**
   - Ensure JIRA_WEBHOOK_SECRET matches JIRA configuration
   - Check webhook secret encoding

3. **High Error Rates**
   - Check system health endpoint
   - Review error logs for patterns
   - Verify external service connectivity

4. **Slow Processing**
   - Monitor hook execution times
   - Check database performance
   - Review hook complexity and conditions

### Debug Mode
Enable debug logging for detailed troubleshooting:
```python
import logging
logging.getLogger('devsync_ai.core.agent_hook_dispatcher').setLevel(logging.DEBUG)
logging.getLogger('devsync_ai.webhooks.jira_webhook_handler').setLevel(logging.DEBUG)
```

## Performance Optimization

### Best Practices
1. **Hook Conditions**: Use specific conditions to reduce unnecessary processing
2. **Rate Limiting**: Configure appropriate rate limits for your JIRA instance
3. **Database Indexing**: Index frequently queried fields in hook execution tables
4. **Caching**: Cache team configurations and hook rules
5. **Monitoring**: Regularly monitor system metrics and performance

### Scaling Considerations
- **Horizontal Scaling**: Deploy multiple instances behind a load balancer
- **Database Optimization**: Use read replicas for analytics queries
- **Queue Processing**: Use message queues for high-volume environments
- **Caching Layer**: Implement Redis for configuration and state caching

## Integration with Existing Systems

The JIRA Webhook Agent Hooks system integrates seamlessly with:
- **Enhanced Notification System**: For intelligent notification routing
- **SlackMessageFormatterFactory**: For rich message formatting
- **JIRA Service**: For additional ticket data and operations
- **Database Layer**: For persistent storage and analytics
- **Monitoring Systems**: For health checks and metrics collection

This system provides a robust, scalable, and intelligent solution for JIRA-to-Slack automation that enhances team productivity and communication.