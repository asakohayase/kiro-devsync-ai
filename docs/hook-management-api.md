# Hook Management API Documentation

This document provides comprehensive documentation for the Hook Management API endpoints, which enable configuration, monitoring, and analytics for JIRA Agent Hooks.

## Overview

The Hook Management API provides the following capabilities:

- **Hook Status Monitoring**: Get real-time status and health information for hooks
- **Execution History**: Access detailed execution logs and performance data
- **Analytics & Performance**: Generate reports and analyze hook performance
- **Alert Management**: Monitor and manage system alerts
- **Configuration Management**: Manage team configurations and rules
- **System Health**: Monitor overall system health and statistics

## Base URL

All endpoints are prefixed with `/api/v1/hooks`

## Authentication

All endpoints require API key authentication via the `Authorization` header:

```
Authorization: Bearer <your-api-key>
```

## Endpoints

### Hook Status and Health

#### GET /status

Get status of all hooks with optional filtering.

**Query Parameters:**
- `team_filter` (optional): Filter by team ID
- `hook_type_filter` (optional): Filter by hook type
- `status_filter` (optional): Filter by status

**Response:**
```json
[
  {
    "hook_id": "hook-123",
    "hook_type": "StatusChangeHook",
    "team_id": "engineering",
    "status": "active",
    "enabled": true,
    "last_execution": "2024-01-15T10:30:00Z",
    "total_executions": 150,
    "success_rate": 0.96,
    "average_execution_time_ms": 1200.0,
    "health_status": "healthy",
    "metadata": {}
  }
]
```

#### GET /status/{hook_id}

Get status of a specific hook.

**Path Parameters:**
- `hook_id`: Hook identifier

**Response:**
```json
{
  "hook_id": "hook-123",
  "hook_type": "StatusChangeHook",
  "team_id": "engineering",
  "status": "active",
  "enabled": true,
  "last_execution": "2024-01-15T10:30:00Z",
  "total_executions": 150,
  "success_rate": 0.96,
  "average_execution_time_ms": 1200.0,
  "health_status": "healthy",
  "metadata": {}
}
```

#### GET /health

Get overall system health status.

**Response:**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "overall_status": "healthy",
  "total_hooks": 25,
  "active_hooks": 23,
  "total_executions": 1500,
  "overall_success_rate": 0.97,
  "average_execution_time_ms": 1100.0,
  "executions_per_minute": 5.2,
  "error_count_last_hour": 2,
  "alerts_count": 1,
  "details": {
    "inactive_hooks": 2,
    "error_rate": 0.03,
    "health_score": 0.95
  }
}
```

### Hook Execution History

#### GET /executions

Get hook execution history with filtering and pagination.

**Query Parameters:**
- `hook_id` (optional): Filter by hook ID
- `team_id` (optional): Filter by team ID
- `status` (optional): Filter by execution status
- `start_time` (optional): Start time for filtering (ISO 8601)
- `end_time` (optional): End time for filtering (ISO 8601)
- `limit` (optional, default: 50): Maximum number of results (1-1000)
- `offset` (optional, default: 0): Offset for pagination

**Response:**
```json
[
  {
    "execution_id": "exec-456",
    "hook_id": "hook-123",
    "hook_type": "StatusChangeHook",
    "team_id": "engineering",
    "event_type": "jira:issue_updated",
    "status": "SUCCESS",
    "started_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:30:01.5Z",
    "execution_time_ms": 1500.0,
    "notification_sent": true,
    "success": true,
    "errors": [],
    "metadata": {
      "event_id": "event-789",
      "ticket_key": "PROJ-123"
    }
  }
]
```

#### GET /executions/{execution_id}

Get details of a specific hook execution.

**Path Parameters:**
- `execution_id`: Execution identifier

**Response:**
```json
{
  "execution_id": "exec-456",
  "hook_id": "hook-123",
  "hook_type": "StatusChangeHook",
  "team_id": "engineering",
  "event_type": "jira:issue_updated",
  "status": "SUCCESS",
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:30:01.5Z",
  "execution_time_ms": 1500.0,
  "notification_sent": true,
  "success": true,
  "errors": [],
  "metadata": {
    "event_id": "event-789",
    "ticket_key": "PROJ-123",
    "notification_result": {
      "channel": "#engineering",
      "message_ts": "1642248601.123456"
    }
  }
}
```

### Analytics and Performance

#### GET /analytics/performance

Generate comprehensive performance report.

**Query Parameters:**
- `start_time` (optional): Start time for report (ISO 8601)
- `end_time` (optional): End time for report (ISO 8601)
- `team_filter` (optional): Filter by team ID
- `hook_type_filter` (optional): Filter by hook type

**Response:**
```json
{
  "report_generated_at": "2024-01-15T10:30:00Z",
  "time_range": {
    "start": "2024-01-08T10:30:00Z",
    "end": "2024-01-15T10:30:00Z"
  },
  "filters": {
    "team_filter": null,
    "hook_type_filter": null
  },
  "summary": {
    "total_hooks": 25,
    "total_executions": 1500,
    "successful_executions": 1455,
    "overall_success_rate": 0.97,
    "average_execution_time_ms": 1100.0,
    "unique_teams": 5,
    "unique_hook_types": 4
  },
  "hook_metrics": [
    {
      "hook_id": "hook-123",
      "total_executions": 150,
      "success_rate": 0.96,
      "average_execution_time_ms": 1200.0
    }
  ],
  "performance_trends": [
    {
      "metric_name": "success_rate",
      "trend_direction": "improving",
      "change_percentage": 2.5
    }
  ],
  "top_performers": [
    {
      "hook_id": "hook-456",
      "success_rate": 0.99,
      "average_execution_time_ms": 800.0
    }
  ],
  "underperformers": [
    {
      "hook_id": "hook-789",
      "success_rate": 0.85,
      "average_execution_time_ms": 2500.0
    }
  ],
  "alerts_summary": {
    "total_alerts": 3,
    "critical_alerts": 1,
    "warning_alerts": 2
  }
}
```

#### GET /analytics/metrics/{hook_id}

Get detailed performance metrics for a specific hook.

**Path Parameters:**
- `hook_id`: Hook identifier

**Query Parameters:**
- `start_time` (optional): Start time for metrics (ISO 8601)
- `end_time` (optional): End time for metrics (ISO 8601)

**Response:**
```json
{
  "hook_id": "hook-123",
  "hook_type": "StatusChangeHook",
  "team_id": "engineering",
  "time_range": {
    "start": "2024-01-14T10:30:00Z",
    "end": "2024-01-15T10:30:00Z"
  },
  "metrics": {
    "total_executions": 150,
    "successful_executions": 144,
    "failed_executions": 6,
    "success_rate": 0.96,
    "error_rate": 0.04,
    "average_execution_time_ms": 1200.0,
    "min_execution_time_ms": 500.0,
    "max_execution_time_ms": 3000.0,
    "executions_per_hour": 6.25,
    "last_execution": "2024-01-15T10:25:00Z",
    "health_status": "healthy"
  }
}
```

### Alert Management

#### GET /alerts

Get alerts with optional filtering.

**Query Parameters:**
- `severity` (optional): Filter by severity (info, warning, critical, error)
- `team_filter` (optional): Filter by team ID
- `resolved` (optional): Filter by resolution status (true/false)

**Response:**
```json
[
  {
    "alert_id": "alert-123",
    "rule_id": "execution_time_warning",
    "hook_id": "hook-456",
    "team_id": "engineering",
    "severity": "warning",
    "title": "High Execution Time",
    "description": "Hook execution time exceeds warning threshold",
    "metric_value": 2500.0,
    "threshold_value": 2000.0,
    "triggered_at": "2024-01-15T10:30:00Z",
    "resolved_at": null,
    "acknowledged": false,
    "metadata": {}
  }
]
```

#### POST /alerts/{alert_id}/acknowledge

Acknowledge an alert.

**Path Parameters:**
- `alert_id`: Alert identifier

**Response:**
```json
{
  "success": true,
  "message": "Alert alert-123 acknowledged"
}
```

#### POST /alerts/{alert_id}/resolve

Resolve an alert.

**Path Parameters:**
- `alert_id`: Alert identifier

**Response:**
```json
{
  "success": true,
  "message": "Alert alert-123 resolved"
}
```

### Configuration Management

#### GET /config/teams

Get list of all configured teams.

**Response:**
```json
["engineering", "qa", "product", "design"]
```

#### GET /config/teams/{team_id}

Get configuration for a specific team.

**Path Parameters:**
- `team_id`: Team identifier

**Response:**
```json
{
  "team_id": "engineering",
  "team_name": "Engineering Team",
  "enabled": true,
  "version": "1.0.0",
  "default_channels": {
    "general": "#engineering",
    "alerts": "#engineering-alerts"
  },
  "notification_preferences": {
    "urgency_threshold": "high",
    "batch_notifications": true
  },
  "business_hours": {
    "start": "09:00",
    "end": "17:00",
    "timezone": "UTC"
  },
  "escalation_rules": [
    {
      "condition": "critical_alert",
      "action": "immediate_notification",
      "channels": ["#engineering-alerts"]
    }
  ],
  "rules": [
    {
      "id": "rule-1",
      "name": "Status Change Rule",
      "enabled": true,
      "hook_types": ["StatusChangeHook"],
      "conditions": [
        {
          "field": "priority",
          "operator": "in",
          "values": ["High", "Critical"]
        }
      ]
    }
  ],
  "last_updated": "2024-01-15T10:30:00Z",
  "metadata": {}
}
```

### System Statistics

#### GET /stats

Get comprehensive hook system statistics.

**Response:**
```json
{
  "system_health": {
    "overall_status": "healthy",
    "total_hooks": 25,
    "active_hooks": 23,
    "total_executions": 1500,
    "overall_success_rate": 0.97,
    "alerts_count": 3
  },
  "configuration": {
    "total_teams": 5,
    "enabled_teams": 5,
    "disabled_teams": 0,
    "total_rules": 15,
    "enabled_rules": 14,
    "disabled_rules": 1,
    "avg_rules_per_team": 3.0,
    "hook_type_distribution": {
      "StatusChangeHook": 8,
      "AssignmentHook": 4,
      "CommentHook": 2,
      "BlockerHook": 1
    }
  },
  "performance": {
    "average_execution_time_ms": 1100.0,
    "executions_per_minute": 5.2,
    "error_count_last_hour": 2
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Error Responses

All endpoints return standard HTTP status codes and error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid severity: invalid_value"
}
```

### 404 Not Found
```json
{
  "detail": "Hook not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to retrieve hook statuses"
}
```

### 503 Service Unavailable
```json
{
  "detail": "Hook registry not available"
}
```

## Rate Limiting

API endpoints are subject to rate limiting:
- 1000 requests per hour per API key
- 100 requests per minute per API key

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642248601
```

## Pagination

Endpoints that return lists support pagination:
- Use `limit` parameter to control page size (max 1000)
- Use `offset` parameter to skip results
- Total count is included in response headers when available

## Filtering and Sorting

Many endpoints support filtering and sorting:
- Time-based filters use ISO 8601 format
- String filters support exact matching
- Results are typically sorted by timestamp (newest first)

## WebSocket Support

Real-time updates are available via WebSocket connections:
- Connect to `/ws/hooks` for real-time hook status updates
- Connect to `/ws/alerts` for real-time alert notifications
- Authentication required via query parameter: `?token=<api-key>`

## SDK and Client Libraries

Official client libraries are available for:
- Python: `pip install devsync-ai-client`
- JavaScript/Node.js: `npm install @devsync-ai/client`
- Go: `go get github.com/devsync-ai/go-client`

## Examples

### Get Hook Status with cURL

```bash
curl -H "Authorization: Bearer your-api-key" \
     "https://api.devsync-ai.com/api/v1/hooks/status?team_filter=engineering"
```

### Get Performance Report with Python

```python
import requests

headers = {"Authorization": "Bearer your-api-key"}
params = {
    "start_time": "2024-01-08T00:00:00Z",
    "end_time": "2024-01-15T23:59:59Z",
    "team_filter": "engineering"
}

response = requests.get(
    "https://api.devsync-ai.com/api/v1/hooks/analytics/performance",
    headers=headers,
    params=params
)

report = response.json()
print(f"Success rate: {report['summary']['overall_success_rate']}")
```

### Acknowledge Alert with JavaScript

```javascript
const response = await fetch(
  'https://api.devsync-ai.com/api/v1/hooks/alerts/alert-123/acknowledge',
  {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer your-api-key',
      'Content-Type': 'application/json'
    }
  }
);

const result = await response.json();
console.log(result.message);
```

## Support

For API support and questions:
- Documentation: https://docs.devsync-ai.com
- Support: support@devsync-ai.com
- GitHub Issues: https://github.com/devsync-ai/api-issues