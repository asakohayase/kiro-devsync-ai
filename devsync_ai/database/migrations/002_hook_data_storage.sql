-- Migration: Hook Data Storage Schema
-- Description: Creates comprehensive database schema for JIRA Agent Hook data storage
-- This migration creates tables for hook executions, team configurations, and performance metrics

-- Enable UUID extension for generating UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Hook executions table for detailed execution tracking
CREATE TABLE IF NOT EXISTS hook_executions (
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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_execution_time CHECK (
        (completed_at IS NULL AND execution_time_ms IS NULL) OR
        (completed_at IS NOT NULL AND execution_time_ms IS NOT NULL AND execution_time_ms >= 0)
    ),
    CONSTRAINT valid_completion_time CHECK (completed_at IS NULL OR completed_at >= started_at),
    CONSTRAINT valid_hook_id CHECK (hook_id != ''),
    CONSTRAINT valid_execution_id CHECK (execution_id != ''),
    CONSTRAINT valid_team_id CHECK (team_id != '')
);

-- Create indexes for hook_executions
CREATE INDEX IF NOT EXISTS idx_hook_executions_hook_id ON hook_executions(hook_id);
CREATE INDEX IF NOT EXISTS idx_hook_executions_team_id ON hook_executions(team_id);
CREATE INDEX IF NOT EXISTS idx_hook_executions_hook_type ON hook_executions(hook_type);
CREATE INDEX IF NOT EXISTS idx_hook_executions_status ON hook_executions(status);
CREATE INDEX IF NOT EXISTS idx_hook_executions_started_at ON hook_executions(started_at);
CREATE INDEX IF NOT EXISTS idx_hook_executions_execution_time ON hook_executions(execution_time_ms);
CREATE INDEX IF NOT EXISTS idx_hook_executions_ticket_key ON hook_executions(ticket_key);
CREATE INDEX IF NOT EXISTS idx_hook_executions_event_type ON hook_executions(event_type);

-- Composite indexes for performance queries
CREATE INDEX IF NOT EXISTS idx_hook_executions_performance ON hook_executions(hook_id, started_at, status);
CREATE INDEX IF NOT EXISTS idx_hook_executions_team_performance ON hook_executions(team_id, started_at, status);
CREATE INDEX IF NOT EXISTS idx_hook_executions_hourly ON hook_executions(DATE_TRUNC('hour', started_at), hook_type);

-- Team hook configurations table
CREATE TABLE IF NOT EXISTS team_hook_configurations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    team_id VARCHAR(100) NOT NULL UNIQUE,
    configuration JSONB NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    version VARCHAR(50) DEFAULT '1.0.0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_team_id_config CHECK (team_id != ''),
    CONSTRAINT valid_configuration CHECK (configuration IS NOT NULL AND configuration != '{}'::jsonb)
);

-- Create indexes for team_hook_configurations
CREATE INDEX IF NOT EXISTS idx_team_hook_configurations_team_id ON team_hook_configurations(team_id);
CREATE INDEX IF NOT EXISTS idx_team_hook_configurations_enabled ON team_hook_configurations(enabled);
CREATE INDEX IF NOT EXISTS idx_team_hook_configurations_updated_at ON team_hook_configurations(updated_at);

-- Create GIN index for JSONB configuration queries
CREATE INDEX IF NOT EXISTS idx_team_hook_configurations_config_gin ON team_hook_configurations USING GIN (configuration);

-- Hook performance metrics table for aggregated metrics
CREATE TABLE IF NOT EXISTS hook_performance_metrics (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    hook_id VARCHAR(255) NOT NULL,
    hook_type VARCHAR(100) NOT NULL,
    team_id VARCHAR(100) NOT NULL,
    time_bucket TIMESTAMP WITH TIME ZONE NOT NULL, -- Hourly buckets
    total_executions INTEGER DEFAULT 0 CHECK (total_executions >= 0),
    successful_executions INTEGER DEFAULT 0 CHECK (successful_executions >= 0),
    failed_executions INTEGER DEFAULT 0 CHECK (failed_executions >= 0),
    avg_execution_time_ms FLOAT DEFAULT 0 CHECK (avg_execution_time_ms >= 0),
    min_execution_time_ms FLOAT DEFAULT 0 CHECK (min_execution_time_ms >= 0),
    max_execution_time_ms FLOAT DEFAULT 0 CHECK (max_execution_time_ms >= 0),
    p95_execution_time_ms FLOAT DEFAULT 0 CHECK (p95_execution_time_ms >= 0),
    success_rate FLOAT DEFAULT 0 CHECK (success_rate >= 0 AND success_rate <= 1),
    error_rate FLOAT DEFAULT 0 CHECK (error_rate >= 0 AND error_rate <= 1),
    throughput_per_hour FLOAT DEFAULT 0 CHECK (throughput_per_hour >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_execution_counts CHECK (
        total_executions = successful_executions + failed_executions
    ),
    CONSTRAINT valid_rates CHECK (
        ABS(success_rate + error_rate - 1.0) < 0.001 OR total_executions = 0
    ),
    CONSTRAINT valid_hook_id_metrics CHECK (hook_id != ''),
    CONSTRAINT valid_team_id_metrics CHECK (team_id != '')
);

-- Create indexes for hook_performance_metrics
CREATE INDEX IF NOT EXISTS idx_hook_performance_metrics_hook_id ON hook_performance_metrics(hook_id);
CREATE INDEX IF NOT EXISTS idx_hook_performance_metrics_team_id ON hook_performance_metrics(team_id);
CREATE INDEX IF NOT EXISTS idx_hook_performance_metrics_time_bucket ON hook_performance_metrics(time_bucket);
CREATE INDEX IF NOT EXISTS idx_hook_performance_metrics_hook_type ON hook_performance_metrics(hook_type);

-- Unique constraint for aggregation
CREATE UNIQUE INDEX IF NOT EXISTS idx_hook_performance_metrics_unique ON hook_performance_metrics(hook_id, time_bucket);

-- Create function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_hook_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_team_hook_configurations_updated_at 
    BEFORE UPDATE ON team_hook_configurations 
    FOR EACH ROW 
    EXECUTE FUNCTION update_hook_updated_at_column();

CREATE TRIGGER update_hook_performance_metrics_updated_at 
    BEFORE UPDATE ON hook_performance_metrics 
    FOR EACH ROW 
    EXECUTE FUNCTION update_hook_updated_at_column();

-- Function to validate team configuration JSON structure
CREATE OR REPLACE FUNCTION validate_team_hook_configuration(config JSONB)
RETURNS BOOLEAN AS $$
BEGIN
    -- Check required fields
    IF NOT (config ? 'team_name') THEN
        RAISE EXCEPTION 'Configuration must contain team_name';
    END IF;
    
    IF NOT (config ? 'default_channels') THEN
        RAISE EXCEPTION 'Configuration must contain default_channels';
    END IF;
    
    IF NOT (config ? 'rules') THEN
        RAISE EXCEPTION 'Configuration must contain rules';
    END IF;
    
    -- Validate rules structure
    IF NOT (config->'rules' @> '[]'::jsonb) THEN
        RAISE EXCEPTION 'Rules must be an array';
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Add constraint to validate configuration structure
ALTER TABLE team_hook_configurations 
ADD CONSTRAINT check_valid_configuration 
CHECK (validate_team_hook_configuration(configuration));

-- Function to get team configuration with fallback to default
CREATE OR REPLACE FUNCTION get_team_hook_configuration(team_id_param VARCHAR(100))
RETURNS JSONB AS $$
DECLARE
    config JSONB;
    default_config JSONB;
BEGIN
    -- Try to get team-specific configuration
    SELECT configuration INTO config
    FROM team_hook_configurations
    WHERE team_id = team_id_param AND enabled = TRUE;
    
    -- If not found, return default configuration
    IF config IS NULL THEN
        default_config := jsonb_build_object(
            'team_name', team_id_param || ' Team',
            'default_channels', jsonb_build_object(
                'status_change', '#' || team_id_param || '-updates',
                'assignment', '#' || team_id_param || '-assignments',
                'comment', '#' || team_id_param || '-discussions',
                'blocker', '#' || team_id_param || '-alerts',
                'general', '#' || team_id_param
            ),
            'notification_preferences', jsonb_build_object(
                'batch_threshold', 3,
                'batch_timeout_minutes', 5,
                'quiet_hours', jsonb_build_object(
                    'enabled', true,
                    'start', '22:00',
                    'end', '08:00'
                ),
                'weekend_notifications', false
            ),
            'business_hours', jsonb_build_object(
                'start', '09:00',
                'end', '17:00',
                'timezone', 'UTC',
                'days', jsonb_build_array('monday', 'tuesday', 'wednesday', 'thursday', 'friday')
            ),
            'escalation_rules', jsonb_build_array(),
            'rules', jsonb_build_array(
                jsonb_build_object(
                    'rule_id', 'default_' || team_id_param || '_rule',
                    'name', 'Default ' || team_id_param || ' Updates',
                    'description', 'Default rule for ' || team_id_param || ' team issues',
                    'hook_types', jsonb_build_array('StatusChangeHook', 'AssignmentHook', 'CommentHook'),
                    'enabled', true,
                    'priority', 10,
                    'conditions', jsonb_build_object(
                        'logic', 'and',
                        'conditions', jsonb_build_array(
                            jsonb_build_object(
                                'field', 'event.classification.affected_teams',
                                'operator', 'contains',
                                'value', team_id_param
                            )
                        )
                    ),
                    'metadata', jsonb_build_object(
                        'channels', jsonb_build_array('#' || team_id_param)
                    )
                )
            ),
            'metadata', jsonb_build_object()
        );
        RETURN default_config;
    END IF;
    
    RETURN config;
END;
$$ LANGUAGE plpgsql;

-- Function to get hook performance summary
CREATE OR REPLACE FUNCTION get_hook_performance_summary(
    hook_id_param VARCHAR(255),
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE
)
RETURNS TABLE (
    hook_id VARCHAR(255),
    hook_type VARCHAR(100),
    team_id VARCHAR(100),
    total_executions BIGINT,
    successful_executions BIGINT,
    failed_executions BIGINT,
    success_rate FLOAT,
    avg_execution_time_ms FLOAT,
    p95_execution_time_ms FLOAT,
    throughput_per_hour FLOAT,
    last_execution TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        he.hook_id,
        he.hook_type,
        he.team_id,
        COUNT(*) as total_executions,
        COUNT(*) FILTER (WHERE he.status = 'SUCCESS') as successful_executions,
        COUNT(*) FILTER (WHERE he.status != 'SUCCESS') as failed_executions,
        CASE WHEN COUNT(*) > 0 
             THEN COUNT(*) FILTER (WHERE he.status = 'SUCCESS')::FLOAT / COUNT(*) 
             ELSE 0 END as success_rate,
        AVG(he.execution_time_ms) as avg_execution_time_ms,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY he.execution_time_ms) as p95_execution_time_ms,
        COUNT(*)::FLOAT / EXTRACT(EPOCH FROM (end_time - start_time)) * 3600 as throughput_per_hour,
        MAX(he.started_at) as last_execution
    FROM hook_executions he
    WHERE he.hook_id = hook_id_param
        AND he.started_at >= start_time 
        AND he.started_at <= end_time
    GROUP BY he.hook_id, he.hook_type, he.team_id;
END;
$$ LANGUAGE plpgsql;

-- Function to aggregate hook performance metrics
CREATE OR REPLACE FUNCTION aggregate_hook_performance_metrics(
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE
)
RETURNS INTEGER AS $$
DECLARE
    processed_count INTEGER := 0;
    hour_bucket TIMESTAMP WITH TIME ZONE;
    hook_record RECORD;
BEGIN
    -- Loop through each hour in the time range
    FOR hour_bucket IN 
        SELECT generate_series(
            DATE_TRUNC('hour', start_time),
            DATE_TRUNC('hour', end_time),
            INTERVAL '1 hour'
        )
    LOOP
        -- Aggregate metrics for each hook in this hour
        FOR hook_record IN
            SELECT 
                hook_id,
                hook_type,
                team_id,
                COUNT(*) as total_executions,
                COUNT(*) FILTER (WHERE status = 'SUCCESS') as successful_executions,
                COUNT(*) FILTER (WHERE status != 'SUCCESS') as failed_executions,
                AVG(execution_time_ms) as avg_execution_time_ms,
                MIN(execution_time_ms) as min_execution_time_ms,
                MAX(execution_time_ms) as max_execution_time_ms,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_ms) as p95_execution_time_ms
            FROM hook_executions
            WHERE started_at >= hour_bucket 
                AND started_at < hour_bucket + INTERVAL '1 hour'
                AND execution_time_ms IS NOT NULL
            GROUP BY hook_id, hook_type, team_id
        LOOP
            -- Insert or update aggregated metrics
            INSERT INTO hook_performance_metrics (
                hook_id,
                hook_type,
                team_id,
                time_bucket,
                total_executions,
                successful_executions,
                failed_executions,
                avg_execution_time_ms,
                min_execution_time_ms,
                max_execution_time_ms,
                p95_execution_time_ms,
                success_rate,
                error_rate,
                throughput_per_hour,
                updated_at
            ) VALUES (
                hook_record.hook_id,
                hook_record.hook_type,
                hook_record.team_id,
                hour_bucket,
                hook_record.total_executions,
                hook_record.successful_executions,
                hook_record.failed_executions,
                hook_record.avg_execution_time_ms,
                hook_record.min_execution_time_ms,
                hook_record.max_execution_time_ms,
                hook_record.p95_execution_time_ms,
                CASE WHEN hook_record.total_executions > 0 
                     THEN hook_record.successful_executions::FLOAT / hook_record.total_executions 
                     ELSE 0 END,
                CASE WHEN hook_record.total_executions > 0 
                     THEN hook_record.failed_executions::FLOAT / hook_record.total_executions 
                     ELSE 0 END,
                hook_record.total_executions::FLOAT,
                NOW()
            )
            ON CONFLICT (hook_id, time_bucket) 
            DO UPDATE SET
                total_executions = EXCLUDED.total_executions,
                successful_executions = EXCLUDED.successful_executions,
                failed_executions = EXCLUDED.failed_executions,
                avg_execution_time_ms = EXCLUDED.avg_execution_time_ms,
                min_execution_time_ms = EXCLUDED.min_execution_time_ms,
                max_execution_time_ms = EXCLUDED.max_execution_time_ms,
                p95_execution_time_ms = EXCLUDED.p95_execution_time_ms,
                success_rate = EXCLUDED.success_rate,
                error_rate = EXCLUDED.error_rate,
                throughput_per_hour = EXCLUDED.throughput_per_hour,
                updated_at = NOW();
            
            processed_count := processed_count + 1;
        END LOOP;
    END LOOP;
    
    RETURN processed_count;
END;
$$ LANGUAGE plpgsql;

-- Add comments to tables for documentation
COMMENT ON TABLE hook_executions IS 'Detailed tracking of individual JIRA Agent Hook executions';
COMMENT ON TABLE team_hook_configurations IS 'Team-specific hook configurations and rules';
COMMENT ON TABLE hook_performance_metrics IS 'Aggregated performance metrics by hook and time bucket';

-- Add comments to important columns
COMMENT ON COLUMN hook_executions.execution_id IS 'Unique identifier for this specific execution instance';
COMMENT ON COLUMN hook_executions.metadata IS 'Additional execution context and debugging information';
COMMENT ON COLUMN hook_executions.notification_result IS 'Result of notification delivery attempt';
COMMENT ON COLUMN team_hook_configurations.configuration IS 'JSONB configuration containing rules, channels, and preferences';
COMMENT ON COLUMN hook_performance_metrics.time_bucket IS 'Hourly time bucket for metric aggregation';
COMMENT ON COLUMN hook_performance_metrics.p95_execution_time_ms IS '95th percentile execution time in milliseconds';

-- Add comments to functions
COMMENT ON FUNCTION validate_team_hook_configuration IS 'Validates team configuration JSON structure';
COMMENT ON FUNCTION get_team_hook_configuration IS 'Gets team configuration with fallback to default';
COMMENT ON FUNCTION get_hook_performance_summary IS 'Returns performance summary for a specific hook';
COMMENT ON FUNCTION aggregate_hook_performance_metrics IS 'Aggregates raw execution data into hourly performance metrics';