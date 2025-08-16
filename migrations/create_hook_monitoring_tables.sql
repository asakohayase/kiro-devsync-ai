-- Migration: Create hook monitoring and analytics tables
-- Description: Creates comprehensive tables for JIRA Agent Hook monitoring, analytics, and alerting

-- Enable RLS (Row Level Security)
ALTER DATABASE postgres SET row_security = on;

-- Create hook_executions table for detailed execution tracking
CREATE TABLE IF NOT EXISTS hook_executions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    hook_id VARCHAR(255) NOT NULL,
    execution_id VARCHAR(255) NOT NULL,
    hook_type VARCHAR(100) NOT NULL,
    team_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_id VARCHAR(255),
    status VARCHAR(50) NOT NULL, -- SUCCESS, FAILED, TIMEOUT, CANCELLED
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    execution_time_ms FLOAT,
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_result JSONB,
    errors JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for hook_executions
CREATE INDEX IF NOT EXISTS idx_hook_executions_hook_id ON hook_executions(hook_id);
CREATE INDEX IF NOT EXISTS idx_hook_executions_team_id ON hook_executions(team_id);
CREATE INDEX IF NOT EXISTS idx_hook_executions_hook_type ON hook_executions(hook_type);
CREATE INDEX IF NOT EXISTS idx_hook_executions_status ON hook_executions(status);
CREATE INDEX IF NOT EXISTS idx_hook_executions_started_at ON hook_executions(started_at);
CREATE INDEX IF NOT EXISTS idx_hook_executions_execution_time ON hook_executions(execution_time_ms);

-- Composite indexes for performance queries
CREATE INDEX IF NOT EXISTS idx_hook_executions_performance ON hook_executions(hook_id, started_at, status);
CREATE INDEX IF NOT EXISTS idx_hook_executions_team_performance ON hook_executions(team_id, started_at, status);
CREATE INDEX IF NOT EXISTS idx_hook_executions_hourly ON hook_executions(DATE_TRUNC('hour', started_at), hook_type);

-- Create hook_performance_metrics table for aggregated metrics
CREATE TABLE IF NOT EXISTS hook_performance_metrics (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    hook_id VARCHAR(255) NOT NULL,
    hook_type VARCHAR(100) NOT NULL,
    team_id VARCHAR(100) NOT NULL,
    time_bucket TIMESTAMP WITH TIME ZONE NOT NULL, -- Hourly buckets
    total_executions INTEGER DEFAULT 0,
    successful_executions INTEGER DEFAULT 0,
    failed_executions INTEGER DEFAULT 0,
    avg_execution_time_ms FLOAT DEFAULT 0,
    min_execution_time_ms FLOAT DEFAULT 0,
    max_execution_time_ms FLOAT DEFAULT 0,
    p95_execution_time_ms FLOAT DEFAULT 0,
    success_rate FLOAT DEFAULT 0,
    error_rate FLOAT DEFAULT 0,
    throughput_per_hour FLOAT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for hook_performance_metrics
CREATE INDEX IF NOT EXISTS idx_hook_performance_metrics_hook_id ON hook_performance_metrics(hook_id);
CREATE INDEX IF NOT EXISTS idx_hook_performance_metrics_team_id ON hook_performance_metrics(team_id);
CREATE INDEX IF NOT EXISTS idx_hook_performance_metrics_time_bucket ON hook_performance_metrics(time_bucket);

-- Unique constraint for aggregation
CREATE UNIQUE INDEX IF NOT EXISTS idx_hook_performance_metrics_unique 
ON hook_performance_metrics(hook_id, time_bucket);

-- Create business_metrics table for business impact tracking
CREATE TABLE IF NOT EXISTS business_metrics (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    team_id VARCHAR(100) NOT NULL,
    metric_type VARCHAR(100) NOT NULL, -- notification_delivery_rate, response_time_improvement, etc.
    metric_value FLOAT NOT NULL,
    time_bucket TIMESTAMP WITH TIME ZONE NOT NULL, -- Daily buckets
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for business_metrics
CREATE INDEX IF NOT EXISTS idx_business_metrics_team_id ON business_metrics(team_id);
CREATE INDEX IF NOT EXISTS idx_business_metrics_type ON business_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_business_metrics_time_bucket ON business_metrics(time_bucket);

-- Unique constraint for daily metrics
CREATE UNIQUE INDEX IF NOT EXISTS idx_business_metrics_unique 
ON business_metrics(team_id, metric_type, time_bucket);

-- Create hook_alerts table for alert management
CREATE TABLE IF NOT EXISTS hook_alerts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    alert_id VARCHAR(255) NOT NULL UNIQUE,
    rule_id VARCHAR(255) NOT NULL,
    hook_id VARCHAR(255),
    team_id VARCHAR(100),
    severity VARCHAR(50) NOT NULL, -- INFO, WARNING, CRITICAL, ERROR
    title VARCHAR(500) NOT NULL,
    description TEXT,
    metric_value FLOAT,
    threshold_value FLOAT,
    triggered_at TIMESTAMP WITH TIME ZONE NOT NULL,
    resolved_at TIMESTAMP WITH TIME ZONE,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for hook_alerts
CREATE INDEX IF NOT EXISTS idx_hook_alerts_rule_id ON hook_alerts(rule_id);
CREATE INDEX IF NOT EXISTS idx_hook_alerts_hook_id ON hook_alerts(hook_id);
CREATE INDEX IF NOT EXISTS idx_hook_alerts_team_id ON hook_alerts(team_id);
CREATE INDEX IF NOT EXISTS idx_hook_alerts_severity ON hook_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_hook_alerts_triggered_at ON hook_alerts(triggered_at);
CREATE INDEX IF NOT EXISTS idx_hook_alerts_resolved_at ON hook_alerts(resolved_at);

-- Index for active alerts
CREATE INDEX IF NOT EXISTS idx_hook_alerts_active ON hook_alerts(triggered_at) WHERE resolved_at IS NULL;

-- Create system_health_snapshots table for system-wide monitoring
CREATE TABLE IF NOT EXISTS system_health_snapshots (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    total_hooks INTEGER DEFAULT 0,
    active_hooks INTEGER DEFAULT 0,
    total_executions INTEGER DEFAULT 0,
    overall_success_rate FLOAT DEFAULT 0,
    avg_execution_time_ms FLOAT DEFAULT 0,
    executions_per_minute FLOAT DEFAULT 0,
    error_count_last_hour INTEGER DEFAULT 0,
    health_status VARCHAR(50) NOT NULL, -- HEALTHY, WARNING, CRITICAL, ERROR
    alerts_count INTEGER DEFAULT 0,
    cpu_usage FLOAT DEFAULT 0,
    memory_usage FLOAT DEFAULT 0,
    queue_depth INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for system_health_snapshots
CREATE INDEX IF NOT EXISTS idx_system_health_snapshots_timestamp ON system_health_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_health_snapshots_health_status ON system_health_snapshots(health_status);

-- Create webhook_processing_stats table for webhook monitoring
CREATE TABLE IF NOT EXISTS webhook_processing_stats (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    webhook_type VARCHAR(100) NOT NULL, -- jira, github, etc.
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    processing_time_ms FLOAT NOT NULL,
    payload_size_bytes INTEGER,
    team_id VARCHAR(100),
    event_type VARCHAR(100),
    hook_triggered BOOLEAN DEFAULT FALSE,
    hook_count INTEGER DEFAULT 0,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for webhook_processing_stats
CREATE INDEX IF NOT EXISTS idx_webhook_processing_stats_webhook_type ON webhook_processing_stats(webhook_type);
CREATE INDEX IF NOT EXISTS idx_webhook_processing_stats_endpoint ON webhook_processing_stats(endpoint);
CREATE INDEX IF NOT EXISTS idx_webhook_processing_stats_status_code ON webhook_processing_stats(status_code);
CREATE INDEX IF NOT EXISTS idx_webhook_processing_stats_timestamp ON webhook_processing_stats(timestamp);
CREATE INDEX IF NOT EXISTS idx_webhook_processing_stats_team_id ON webhook_processing_stats(team_id);

-- Composite index for performance analysis
CREATE INDEX IF NOT EXISTS idx_webhook_processing_stats_performance 
ON webhook_processing_stats(webhook_type, timestamp, processing_time_ms);

-- Create RLS policies

-- hook_executions policies
ALTER TABLE hook_executions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "hook_executions_select_policy" ON hook_executions
    FOR SELECT USING (true);

CREATE POLICY "hook_executions_insert_policy" ON hook_executions
    FOR INSERT WITH CHECK (true);

CREATE POLICY "hook_executions_delete_policy" ON hook_executions
    FOR DELETE USING (created_at < NOW() - INTERVAL '90 days');

-- hook_performance_metrics policies
ALTER TABLE hook_performance_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "hook_performance_metrics_select_policy" ON hook_performance_metrics
    FOR SELECT USING (true);

CREATE POLICY "hook_performance_metrics_insert_policy" ON hook_performance_metrics
    FOR INSERT WITH CHECK (true);

CREATE POLICY "hook_performance_metrics_update_policy" ON hook_performance_metrics
    FOR UPDATE USING (true);

CREATE POLICY "hook_performance_metrics_delete_policy" ON hook_performance_metrics
    FOR DELETE USING (created_at < NOW() - INTERVAL '180 days');

-- business_metrics policies
ALTER TABLE business_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "business_metrics_select_policy" ON business_metrics
    FOR SELECT USING (true);

CREATE POLICY "business_metrics_insert_policy" ON business_metrics
    FOR INSERT WITH CHECK (true);

CREATE POLICY "business_metrics_update_policy" ON business_metrics
    FOR UPDATE USING (true);

CREATE POLICY "business_metrics_delete_policy" ON business_metrics
    FOR DELETE USING (created_at < NOW() - INTERVAL '365 days');

-- hook_alerts policies
ALTER TABLE hook_alerts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "hook_alerts_select_policy" ON hook_alerts
    FOR SELECT USING (true);

CREATE POLICY "hook_alerts_insert_policy" ON hook_alerts
    FOR INSERT WITH CHECK (true);

CREATE POLICY "hook_alerts_update_policy" ON hook_alerts
    FOR UPDATE USING (true);

CREATE POLICY "hook_alerts_delete_policy" ON hook_alerts
    FOR DELETE USING (created_at < NOW() - INTERVAL '90 days');

-- system_health_snapshots policies
ALTER TABLE system_health_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "system_health_snapshots_select_policy" ON system_health_snapshots
    FOR SELECT USING (true);

CREATE POLICY "system_health_snapshots_insert_policy" ON system_health_snapshots
    FOR INSERT WITH CHECK (true);

CREATE POLICY "system_health_snapshots_delete_policy" ON system_health_snapshots
    FOR DELETE USING (created_at < NOW() - INTERVAL '30 days');

-- webhook_processing_stats policies
ALTER TABLE webhook_processing_stats ENABLE ROW LEVEL SECURITY;

CREATE POLICY "webhook_processing_stats_select_policy" ON webhook_processing_stats
    FOR SELECT USING (true);

CREATE POLICY "webhook_processing_stats_insert_policy" ON webhook_processing_stats
    FOR INSERT WITH CHECK (true);

CREATE POLICY "webhook_processing_stats_delete_policy" ON webhook_processing_stats
    FOR DELETE USING (created_at < NOW() - INTERVAL '90 days');

-- Create analytics functions

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

-- Function to get team productivity metrics
CREATE OR REPLACE FUNCTION get_team_productivity_metrics(
    team_id_param VARCHAR(100),
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE
)
RETURNS TABLE (
    team_id VARCHAR(100),
    total_hooks BIGINT,
    active_hooks BIGINT,
    total_executions BIGINT,
    avg_response_time_ms FLOAT,
    productivity_score FLOAT,
    notification_delivery_rate FLOAT,
    blocked_ticket_resolution_improvement FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        he.team_id,
        COUNT(DISTINCT he.hook_id) as total_hooks,
        COUNT(DISTINCT he.hook_id) FILTER (
            WHERE he.started_at > start_time + (end_time - start_time) * 0.8
        ) as active_hooks,
        COUNT(*) as total_executions,
        AVG(he.execution_time_ms) as avg_response_time_ms,
        -- Productivity score based on success rate and activity
        CASE WHEN COUNT(*) > 0 
             THEN (COUNT(*) FILTER (WHERE he.status = 'SUCCESS')::FLOAT / COUNT(*)) * 100
             ELSE 0 END as productivity_score,
        -- Notification delivery rate
        CASE WHEN COUNT(*) > 0 
             THEN COUNT(*) FILTER (WHERE he.notification_sent = true)::FLOAT / COUNT(*)
             ELSE 0 END as notification_delivery_rate,
        -- Mock blocked ticket resolution improvement (would be calculated from JIRA data)
        CASE WHEN COUNT(*) > 10 THEN RANDOM() * 20 + 10 ELSE 0 END as blocked_ticket_resolution_improvement
    FROM hook_executions he
    WHERE he.team_id = team_id_param
        AND he.started_at >= start_time 
        AND he.started_at <= end_time
    GROUP BY he.team_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get system health metrics
CREATE OR REPLACE FUNCTION get_current_system_health()
RETURNS TABLE (
    total_hooks BIGINT,
    active_hooks BIGINT,
    executions_last_hour BIGINT,
    success_rate_last_hour FLOAT,
    avg_execution_time_ms FLOAT,
    error_count_last_hour BIGINT,
    health_status VARCHAR(50)
) AS $$
DECLARE
    one_hour_ago TIMESTAMP WITH TIME ZONE := NOW() - INTERVAL '1 hour';
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(DISTINCT he.hook_id) as total_hooks,
        COUNT(DISTINCT he.hook_id) FILTER (WHERE he.started_at > one_hour_ago) as active_hooks,
        COUNT(*) FILTER (WHERE he.started_at > one_hour_ago) as executions_last_hour,
        CASE WHEN COUNT(*) FILTER (WHERE he.started_at > one_hour_ago) > 0
             THEN COUNT(*) FILTER (WHERE he.started_at > one_hour_ago AND he.status = 'SUCCESS')::FLOAT / 
                  COUNT(*) FILTER (WHERE he.started_at > one_hour_ago)
             ELSE 1.0 END as success_rate_last_hour,
        AVG(he.execution_time_ms) FILTER (WHERE he.started_at > one_hour_ago) as avg_execution_time_ms,
        COUNT(*) FILTER (WHERE he.started_at > one_hour_ago AND he.status != 'SUCCESS') as error_count_last_hour,
        CASE 
            WHEN COUNT(*) FILTER (WHERE he.started_at > one_hour_ago AND he.status != 'SUCCESS') > 10 
                 OR AVG(he.execution_time_ms) FILTER (WHERE he.started_at > one_hour_ago) > 5000
                THEN 'CRITICAL'
            WHEN COUNT(*) FILTER (WHERE he.started_at > one_hour_ago AND he.status != 'SUCCESS') > 5 
                 OR AVG(he.execution_time_ms) FILTER (WHERE he.started_at > one_hour_ago) > 2000
                THEN 'WARNING'
            ELSE 'HEALTHY'
        END as health_status
    FROM hook_executions he
    WHERE he.started_at > NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old monitoring data
CREATE OR REPLACE FUNCTION cleanup_old_monitoring_records()
RETURNS TABLE (
    table_name TEXT,
    records_deleted BIGINT
) AS $$
DECLARE
    deleted_count BIGINT;
BEGIN
    -- Clean hook_executions (keep 90 days)
    DELETE FROM hook_executions WHERE created_at < NOW() - INTERVAL '90 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    table_name := 'hook_executions';
    records_deleted := deleted_count;
    RETURN NEXT;
    
    -- Clean hook_performance_metrics (keep 180 days)
    DELETE FROM hook_performance_metrics WHERE created_at < NOW() - INTERVAL '180 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    table_name := 'hook_performance_metrics';
    records_deleted := deleted_count;
    RETURN NEXT;
    
    -- Clean business_metrics (keep 365 days)
    DELETE FROM business_metrics WHERE created_at < NOW() - INTERVAL '365 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    table_name := 'business_metrics';
    records_deleted := deleted_count;
    RETURN NEXT;
    
    -- Clean resolved hook_alerts (keep 90 days)
    DELETE FROM hook_alerts WHERE resolved_at IS NOT NULL AND created_at < NOW() - INTERVAL '90 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    table_name := 'hook_alerts';
    records_deleted := deleted_count;
    RETURN NEXT;
    
    -- Clean system_health_snapshots (keep 30 days)
    DELETE FROM system_health_snapshots WHERE created_at < NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    table_name := 'system_health_snapshots';
    records_deleted := deleted_count;
    RETURN NEXT;
    
    -- Clean webhook_processing_stats (keep 90 days)
    DELETE FROM webhook_processing_stats WHERE created_at < NOW() - INTERVAL '90 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    table_name := 'webhook_processing_stats';
    records_deleted := deleted_count;
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Comments
COMMENT ON TABLE hook_executions IS 'Detailed tracking of individual hook executions';
COMMENT ON TABLE hook_performance_metrics IS 'Aggregated performance metrics by hook and time bucket';
COMMENT ON TABLE business_metrics IS 'Business impact metrics for teams and productivity tracking';
COMMENT ON TABLE hook_alerts IS 'Alert management for hook performance and system health';
COMMENT ON TABLE system_health_snapshots IS 'System-wide health monitoring snapshots';
COMMENT ON TABLE webhook_processing_stats IS 'Webhook processing performance and monitoring';

COMMENT ON FUNCTION aggregate_hook_performance_metrics IS 'Aggregates raw execution data into hourly performance metrics';
COMMENT ON FUNCTION get_hook_performance_summary IS 'Returns performance summary for a specific hook';
COMMENT ON FUNCTION get_team_productivity_metrics IS 'Returns productivity metrics for a team';
COMMENT ON FUNCTION get_current_system_health IS 'Returns current system health status';
COMMENT ON FUNCTION cleanup_old_monitoring_records IS 'Cleans up old monitoring records across all tables';