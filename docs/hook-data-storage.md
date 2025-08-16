# Hook Data Storage Implementation

This document describes the database schema and implementation for JIRA Agent Hook data storage, which provides comprehensive tracking, configuration management, and performance monitoring for the hook system.

## Overview

The hook data storage system provides:

- **Hook Execution Tracking**: Detailed logging of all hook executions with performance metrics
- **Team Configuration Management**: Flexible team-specific hook configurations and rules
- **Performance Metrics**: Aggregated performance data for monitoring and optimization
- **Database Integration**: High-level API for hook data operations

## Database Schema

### Core Tables

#### `hook_executions`
Tracks individual hook execution instances with detailed metadata.

```sql
CREATE TABLE hook_executions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    hook_id VARCHAR(255) NOT NULL,
    execution_id VARCHAR(255) NOT NULL UNIQUE,
    hook_type VARCHAR(100) NOT NULL,
    team_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_id VARCHAR(255),
    ticket_key VARCHAR(50),
    project_key VARCHAR(50),
    status VARCHAR(50) NOT NULL CHECK (status IN ('SUCCESS', 'FAILED', 'TIMEOUT', 'CANCELLED')),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    execution_time_ms FLOAT,
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_result JSONB,
    errors JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Key Features:**
- Unique execution tracking with `execution_id`
- Performance metrics with `execution_time_ms`
- Flexible metadata storage with JSONB
- Comprehensive indexing for fast queries

#### `team_hook_configurations`
Stores team-specific hook configurations and rules.

```sql
CREATE TABLE team_hook_configurations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    team_id VARCHAR(100) NOT NULL UNIQUE,
    configuration JSONB NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    version VARCHAR(50) DEFAULT '1.0.0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Configuration Structure:**
```json
{
  "team_name": "Engineering Team",
  "default_channels": {
    "status_change": "#eng-updates",
    "assignment": "#eng-assignments",
    "comment": "#eng-discussions",
    "blocker": "#eng-alerts"
  },
  "notification_preferences": {
    "batch_threshold": 3,
    "batch_timeout_minutes": 5,
    "quiet_hours": {
      "enabled": true,
      "start": "22:00",
      "end": "08:00"
    }
  },
  "rules": [
    {
      "rule_id": "eng_status_changes",
      "name": "Engineering Status Changes",
      "hook_types": ["StatusChangeHook"],
      "enabled": true,
      "conditions": {
        "logic": "and",
        "conditions": [
          {
            "field": "event.classification.affected_teams",
            "operator": "contains",
            "value": "engineering"
          }
        ]
      }
    }
  ]
}
```

#### `hook_performance_metrics`
Aggregated performance metrics for monitoring and analysis.

```sql
CREATE TABLE hook_performance_metrics (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    hook_id VARCHAR(255) NOT NULL,
    hook_type VARCHAR(100) NOT NULL,
    team_id VARCHAR(100) NOT NULL,
    time_bucket TIMESTAMP WITH TIME ZONE NOT NULL,
    total_executions INTEGER DEFAULT 0,
    successful_executions INTEGER DEFAULT 0,
    failed_executions INTEGER DEFAULT 0,
    avg_execution_time_ms FLOAT DEFAULT 0,
    p95_execution_time_ms FLOAT DEFAULT 0,
    success_rate FLOAT DEFAULT 0,
    throughput_per_hour FLOAT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Database Functions

#### `get_team_hook_configuration(team_id)`
Returns team configuration with fallback to default configuration.

#### `get_hook_performance_summary(hook_id, start_time, end_time)`
Returns comprehensive performance summary for a specific hook.

#### `aggregate_hook_performance_metrics(start_time, end_time)`
Aggregates raw execution data into hourly performance metrics.

## API Reference

### HookDataManager Class

The `HookDataManager` class provides high-level database operations for hook data.

#### Hook Execution Operations

```python
from devsync_ai.database.hook_data_manager import get_hook_data_manager

hook_data_manager = await get_hook_data_manager()

# Create hook execution
execution_id = await hook_data_manager.create_hook_execution(
    hook_id="status_change_hook_v1",
    hook_type="StatusChangeHook",
    team_id="engineering",
    event_type="jira:issue_updated",
    ticket_key="ENG-123",
    metadata={"priority": "high"}
)

# Update hook execution
await hook_data_manager.update_hook_execution(
    execution_id=execution_id,
    status="SUCCESS",
    execution_time_ms=150.5,
    notification_sent=True,
    notification_result={"channel": "#eng-updates", "message_id": "msg_123"}
)

# Get hook execution
execution = await hook_data_manager.get_hook_execution(execution_id)

# Query hook executions
executions = await hook_data_manager.get_hook_executions(
    hook_id="status_change_hook_v1",
    team_id="engineering",
    status="SUCCESS",
    limit=50
)
```

#### Team Configuration Operations

```python
# Get team configuration (with fallback to default)
config = await hook_data_manager.get_team_configuration("engineering")

# Save team configuration
await hook_data_manager.save_team_configuration(
    team_id="engineering",
    configuration={
        "team_name": "Engineering Team",
        "default_channels": {"general": "#engineering"},
        "rules": []
    }
)

# Get all team configurations
all_configs = await hook_data_manager.get_all_team_configurations()
```

#### Performance Metrics Operations

```python
from datetime import datetime, timedelta

# Get performance summary
start_time = datetime.utcnow() - timedelta(hours=24)
end_time = datetime.utcnow()

summary = await hook_data_manager.get_hook_performance_summary(
    hook_id="status_change_hook_v1",
    start_time=start_time,
    end_time=end_time
)

# Aggregate performance metrics
processed_count = await hook_data_manager.aggregate_performance_metrics(
    start_time=start_time,
    end_time=end_time
)

# Get execution statistics
stats = await hook_data_manager.get_execution_statistics(
    team_id="engineering",
    hours=24
)
```

## Migration and Setup

### 1. Database Migration

The hook data storage requires running the database migration to create the necessary tables and functions.

```bash
# Generate combined migration file
python devsync_ai/database/migrations/runner.py

# Apply migration manually in Supabase SQL Editor
# Execute the contents of: devsync_ai/database/migrations/run_migrations.sql
```

### 2. Environment Variables

Ensure the following environment variables are set:

```bash
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_api_key
```

### 3. Migration Script

Use the migration script for guided setup:

```bash
# Run migration script
python scripts/migrate_hook_data_storage.py

# Test the migration
python scripts/migrate_hook_data_storage.py --test
```

## Testing

### Running Tests

The hook data storage includes comprehensive tests covering all functionality:

```bash
# Run all hook data storage tests
python scripts/test_hook_data_storage.py

# Run specific test categories
python scripts/test_hook_data_storage.py --basic
python scripts/test_hook_data_storage.py --performance
python scripts/test_hook_data_storage.py --errors

# Validate implementation without database
python scripts/validate_hook_data_storage.py
```

### Test Coverage

The test suite covers:

- **Database Connection**: Basic connectivity and health checks
- **Hook Execution Lifecycle**: Create, update, query operations
- **Team Configuration Management**: CRUD operations with validation
- **Performance Metrics**: Aggregation and summary generation
- **Error Handling**: Edge cases and error scenarios
- **Concurrent Operations**: Multi-threaded execution safety
- **Integration Testing**: End-to-end workflow validation

## Performance Considerations

### Indexing Strategy

The schema includes comprehensive indexing for optimal query performance:

- **Primary Indexes**: All tables have UUID primary keys
- **Query Indexes**: Indexes on frequently queried columns (hook_id, team_id, status)
- **Composite Indexes**: Multi-column indexes for complex queries
- **Time-based Indexes**: Optimized for time-range queries
- **JSONB Indexes**: GIN indexes for JSONB column queries

### Data Retention

Automatic cleanup functions are provided:

```python
# Clean up old execution records (default: 90 days)
deleted_count = await hook_data_manager.cleanup_old_executions(days=90)
```

### Performance Monitoring

Built-in performance monitoring includes:

- Execution time tracking
- Success/failure rate monitoring
- Throughput measurement
- P95 latency tracking
- Resource utilization metrics

## Integration with Hook System

### Hook Execution Integration

```python
from devsync_ai.database.hook_data_manager import get_hook_data_manager

class BaseAgentHook:
    async def execute_with_tracking(self, event):
        hook_data_manager = await get_hook_data_manager()
        
        # Create execution record
        execution_id = await hook_data_manager.create_hook_execution(
            hook_id=self.hook_id,
            hook_type=self.__class__.__name__,
            team_id=event.team_id,
            event_type=event.event_type,
            ticket_key=event.ticket_key
        )
        
        start_time = time.time()
        try:
            # Execute hook logic
            result = await self.execute(event)
            
            # Update with success
            await hook_data_manager.update_hook_execution(
                execution_id=execution_id,
                status="SUCCESS",
                execution_time_ms=(time.time() - start_time) * 1000,
                notification_sent=result.notification_sent,
                notification_result=result.notification_result
            )
            
            return result
            
        except Exception as e:
            # Update with failure
            await hook_data_manager.update_hook_execution(
                execution_id=execution_id,
                status="FAILED",
                execution_time_ms=(time.time() - start_time) * 1000,
                errors=[str(e)]
            )
            raise
```

### Configuration Integration

```python
from devsync_ai.database.hook_data_manager import get_hook_data_manager

class HookRuleEngine:
    async def get_team_rules(self, team_id: str):
        hook_data_manager = await get_hook_data_manager()
        config = await hook_data_manager.get_team_configuration(team_id)
        return config.get("rules", [])
```

## Monitoring and Alerting

### Health Checks

```python
# System health check
health = await hook_data_manager.health_check()
print(f"Database healthy: {health['database_healthy']}")
print(f"Recent executions: {health['recent_executions_count']}")
```

### Performance Monitoring

```python
# Get execution statistics
stats = await hook_data_manager.get_execution_statistics(hours=24)
print(f"Success rate: {stats['success_rate']:.2%}")
print(f"Average execution time: {stats['avg_execution_time_ms']:.1f}ms")
```

## Troubleshooting

### Common Issues

1. **Migration Failures**
   - Verify Supabase connection
   - Check SQL syntax in migration files
   - Ensure proper permissions

2. **Performance Issues**
   - Check index usage with EXPLAIN ANALYZE
   - Monitor query execution times
   - Consider data retention policies

3. **Configuration Errors**
   - Validate JSON structure
   - Check required fields
   - Verify team ID consistency

### Debug Tools

```python
# Enable debug logging
import logging
logging.getLogger('devsync_ai.database').setLevel(logging.DEBUG)

# Test database connectivity
from devsync_ai.database.connection import get_database
db = await get_database()
healthy = await db.health_check()
```

## Future Enhancements

Planned improvements include:

- **Real-time Analytics**: WebSocket-based real-time metrics
- **Advanced Alerting**: Configurable alert rules and notifications
- **Data Export**: CSV/JSON export functionality
- **Performance Optimization**: Query optimization and caching
- **Backup/Restore**: Automated backup and restore procedures

## Related Documentation

- [JIRA Slack Agent Hooks Design](./jira-webhook-agent-hooks.md)
- [Enhanced Notification System](./enhanced-notification-system.md)
- [Database Setup](./database-setup.md)
- [Analytics System](./analytics-system.md)