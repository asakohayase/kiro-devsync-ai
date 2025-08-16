---
inclusion: fileMatch
fileMatchPattern: ['**/jira*.py', '**/webhooks/*.py', '**/hooks/*.py', '**/agent_hooks.py', '**/jira_*.py', 'config/*jira*.yaml', 'docs/jira*.md']
---

# JIRA Integration Guidelines

## Architecture Patterns

### Event-Driven Processing
- Use the `JiraEventProcessor` for all JIRA webhook event handling
- Implement event classification through `EventClassificationEngine`
- Follow the agent hook pattern for automated responses to JIRA events

### Hook System Design
- All JIRA hooks should extend the base agent hook framework in `devsync_ai/core/agent_hooks.py`
- Use `HookRuleEngine` for conditional logic and event filtering
- Implement proper error handling through `HookErrorHandler`

### Data Flow
```
JIRA Webhook → JiraWebhookHandler → JiraEventProcessor → AgentHookDispatcher → Specific Hook Implementation
```

## Code Conventions

### JIRA Service Integration
- Use the centralized `JiraService` class for all JIRA API interactions
- Implement proper authentication and rate limiting
- Handle JIRA API errors gracefully with retry logic

### Template System
- Use JIRA-specific templates from `devsync_ai/templates/jira_templates.py`
- Follow the template factory pattern for message formatting
- Support both Slack Block Kit and plain text formats

### Configuration Management
- Store JIRA configurations in `config/jira_webhook_config.example.yaml` format
- Use environment variables for sensitive data (API tokens, URLs)
- Implement configuration validation through `HookConfigurationValidator`

## Implementation Rules

### Webhook Processing
- Always validate webhook signatures for security
- Use async processing for webhook handlers to prevent timeouts
- Implement proper logging for debugging webhook issues

### Agent Hook Development
- Register all hooks through `HookRegistryManager`
- Implement proper lifecycle management with `HookLifecycleManager`
- Use the analytics system to track hook performance

### Error Handling
- Use structured error handling with proper error codes
- Implement fallback mechanisms for failed JIRA operations
- Log errors with sufficient context for debugging

### Testing Requirements
- Write integration tests for all JIRA webhook scenarios
- Mock JIRA API responses in unit tests
- Test error conditions and edge cases thoroughly

## Security Practices

### Authentication
- Use OAuth 2.0 or API tokens for JIRA authentication
- Store credentials securely using environment variables
- Implement token refresh mechanisms where applicable

### Data Validation
- Validate all incoming webhook payloads
- Sanitize user input from JIRA fields
- Implement proper access control for hook configurations

## Performance Considerations

### Batching and Threading
- Use message batching for multiple JIRA updates
- Implement proper threading for concurrent webhook processing
- Consider rate limits when making bulk JIRA API calls

### Caching
- Cache JIRA project metadata and user information
- Implement proper cache invalidation strategies
- Use database storage for persistent hook data

## Monitoring and Analytics

### Hook Analytics
- Track hook execution metrics through `HookAnalyticsEngine`
- Monitor JIRA API response times and error rates
- Implement alerting for failed webhook processing

### Business Metrics
- Track team productivity metrics from JIRA data
- Analyze workload distribution and assignment patterns
- Generate insights for process improvementCreate an Agent Steering document for JIRA integration patterns and best practices.

This steering document should guide all JIRA-related code generation and API interactions in our DevSync AI project. Include:

AUTHENTICATION & SECURITY:
- Proper API token handling and storage patterns
- Webhook signature verification for security
- Rate limiting strategies to avoid API throttling
- Error handling for authentication failures

API INTERACTION PATTERNS:
- Consistent JIRA REST API v3 usage patterns
- Proper pagination handling for large datasets
- Efficient field selection to minimize payload sizes
- Batch operations for multiple ticket updates
- Webhook payload parsing and validation

DATA PROCESSING STANDARDS:
- Consistent ticket data structure normalization
- Sprint and project information extraction
- Comment and attachment handling patterns
- Status transition tracking and history

ERROR HANDLING & RESILIENCE:
- Retry logic with exponential backoff
- Circuit breaker patterns for API failures
- Graceful degradation when JIRA is unavailable
- Comprehensive logging for debugging

PERFORMANCE OPTIMIZATION:
- Caching strategies for frequently accessed data
- Async/await patterns for non-blocking operations
- Database query optimization for ticket storage
- Memory management for large webhook payloads

Save this as python-jira-integration-patterns.md in the Agent Steering section.