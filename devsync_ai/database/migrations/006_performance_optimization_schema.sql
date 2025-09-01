-- Performance Optimization and Monitoring Schema
-- Migration: 006_performance_optimization_schema.sql

-- Performance metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_type VARCHAR(50) NOT NULL,
    value DECIMAL NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    metadata JSONB,
    team_id VARCHAR(100),
    operation_id VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Performance alerts table
CREATE TABLE IF NOT EXISTS performance_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id VARCHAR(200) UNIQUE NOT NULL,
    severity VARCHAR(20) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    threshold_value DECIMAL NOT NULL,
    actual_value DECIMAL NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    team_id VARCHAR(100),
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Benchmark results table
CREATE TABLE IF NOT EXISTS benchmark_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    benchmark_id VARCHAR(200) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    benchmark_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds DECIMAL,
    min_time DECIMAL,
    max_time DECIMAL,
    mean_time DECIMAL,
    median_time DECIMAL,
    percentile_95 DECIMAL,
    percentile_99 DECIMAL,
    std_deviation DECIMAL,
    throughput DECIMAL,
    error_rate DECIMAL,
    iterations INTEGER,
    errors JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Capacity alerts table
CREATE TABLE IF NOT EXISTS capacity_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id VARCHAR(200) UNIQUE NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    current_value DECIMAL NOT NULL,
    threshold_value DECIMAL NOT NULL,
    predicted_breach_time TIMESTAMP,
    severity VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Capacity forecasts table
CREATE TABLE IF NOT EXISTS capacity_forecasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(50) NOT NULL,
    current_utilization DECIMAL NOT NULL,
    predicted_utilization JSONB NOT NULL,
    prediction_timestamps JSONB NOT NULL,
    confidence_intervals JSONB,
    model_used VARCHAR(50) NOT NULL,
    accuracy_score DECIMAL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Scaling recommendations table
CREATE TABLE IF NOT EXISTS scaling_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(50) NOT NULL,
    current_capacity DECIMAL NOT NULL,
    recommended_capacity DECIMAL NOT NULL,
    scaling_direction VARCHAR(20) NOT NULL,
    urgency VARCHAR(20) NOT NULL,
    reasoning TEXT NOT NULL,
    implementation_timeline TEXT,
    risk_assessment TEXT,
    executed BOOLEAN DEFAULT FALSE,
    executed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_performance_metrics_type_timestamp
ON performance_metrics(metric_type, timestamp DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_performance_metrics_team_timestamp
ON performance_metrics(team_id, timestamp DESC)
WHERE team_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_performance_metrics_operation
ON performance_metrics(operation_id, timestamp DESC)
WHERE operation_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_performance_alerts_severity_timestamp
ON performance_alerts(severity, timestamp DESC)
WHERE resolved = false;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_performance_alerts_metric_type
ON performance_alerts(metric_type, timestamp DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_benchmark_results_name_start_time
ON benchmark_results(name, start_time DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_benchmark_results_type_status
ON benchmark_results(benchmark_type, status, start_time DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_capacity_alerts_resource_severity
ON capacity_alerts(resource_type, severity, timestamp DESC)
WHERE resolved = false;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_capacity_forecasts_resource_created
ON capacity_forecasts(resource_type, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scaling_recommendations_resource_urgency
ON scaling_recommendations(resource_type, urgency, created_at DESC);

-- Create partitioning for performance_metrics table (by month)
-- This helps with query performance and data management
CREATE TABLE IF NOT EXISTS performance_metrics_template (
    LIKE performance_metrics INCLUDING ALL
);

-- Function to create monthly partitions
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name text, start_date date)
RETURNS void AS $$
DECLARE
    partition_name text;
    end_date date;
BEGIN
    partition_name := table_name || '_' || to_char(start_date, 'YYYY_MM');
    end_date := start_date + interval '1 month';
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF %I
                    FOR VALUES FROM (%L) TO (%L)',
                   partition_name, table_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;

-- Create partitions for current and next month
SELECT create_monthly_partition('performance_metrics', date_trunc('month', CURRENT_DATE));
SELECT create_monthly_partition('performance_metrics', date_trunc('month', CURRENT_DATE + interval '1 month'));

-- Create views for common queries
CREATE OR REPLACE VIEW performance_summary AS
SELECT 
    metric_type,
    COUNT(*) as total_measurements,
    AVG(value) as avg_value,
    MIN(value) as min_value,
    MAX(value) as max_value,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY value) as p95_value,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY value) as p99_value,
    date_trunc('hour', timestamp) as hour_bucket
FROM performance_metrics
WHERE timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY metric_type, date_trunc('hour', timestamp)
ORDER BY hour_bucket DESC, metric_type;

CREATE OR REPLACE VIEW active_performance_alerts AS
SELECT 
    alert_id,
    severity,
    metric_type,
    message,
    actual_value,
    threshold_value,
    timestamp,
    team_id,
    EXTRACT(EPOCH FROM (NOW() - timestamp))/60 as minutes_active
FROM performance_alerts
WHERE resolved = false
ORDER BY 
    CASE severity 
        WHEN 'critical' THEN 1 
        WHEN 'warning' THEN 2 
        ELSE 3 
    END,
    timestamp DESC;

CREATE OR REPLACE VIEW capacity_utilization_current AS
SELECT 
    resource_type,
    current_utilization,
    created_at,
    ROW_NUMBER() OVER (PARTITION BY resource_type ORDER BY created_at DESC) as rn
FROM capacity_forecasts
WHERE created_at >= NOW() - INTERVAL '1 hour';

-- Create materialized view for performance dashboard
CREATE MATERIALIZED VIEW IF NOT EXISTS performance_dashboard_data AS
SELECT 
    'system_health' as metric_category,
    metric_type,
    AVG(value) as current_value,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY value) as p95_value,
    COUNT(*) as sample_count,
    NOW() as last_updated
FROM performance_metrics
WHERE timestamp >= NOW() - INTERVAL '1 hour'
GROUP BY metric_type

UNION ALL

SELECT 
    'alerts' as metric_category,
    severity as metric_type,
    COUNT(*)::decimal as current_value,
    COUNT(*)::decimal as p95_value,
    COUNT(*) as sample_count,
    NOW() as last_updated
FROM performance_alerts
WHERE resolved = false
GROUP BY severity;

-- Create index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_performance_dashboard_category_type
ON performance_dashboard_data(metric_category, metric_type);

-- Refresh materialized view function
CREATE OR REPLACE FUNCTION refresh_performance_dashboard()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY performance_dashboard_data;
END;
$$ LANGUAGE plpgsql;

-- Create function to clean up old performance data
CREATE OR REPLACE FUNCTION cleanup_old_performance_data()
RETURNS void AS $$
BEGIN
    -- Delete performance metrics older than 30 days
    DELETE FROM performance_metrics 
    WHERE timestamp < NOW() - INTERVAL '30 days';
    
    -- Delete resolved alerts older than 7 days
    DELETE FROM performance_alerts 
    WHERE resolved = true AND resolved_at < NOW() - INTERVAL '7 days';
    
    -- Delete old capacity forecasts (keep last 7 days)
    DELETE FROM capacity_forecasts 
    WHERE created_at < NOW() - INTERVAL '7 days';
    
    -- Delete old benchmark results (keep last 90 days)
    DELETE FROM benchmark_results 
    WHERE start_time < NOW() - INTERVAL '90 days';
    
    -- Delete old scaling recommendations (keep last 30 days)
    DELETE FROM scaling_recommendations 
    WHERE created_at < NOW() - INTERVAL '30 days';
    
    -- Vacuum tables to reclaim space
    VACUUM ANALYZE performance_metrics;
    VACUUM ANALYZE performance_alerts;
    VACUUM ANALYZE capacity_forecasts;
    VACUUM ANALYZE benchmark_results;
    VACUUM ANALYZE scaling_recommendations;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO postgres;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO postgres;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO postgres;

-- Insert initial configuration data
INSERT INTO performance_alerts (alert_id, severity, metric_type, threshold_value, actual_value, message, resolved)
VALUES ('system_startup', 'info', 'system_status', 0, 1, 'Performance monitoring system initialized', true)
ON CONFLICT (alert_id) DO NOTHING;

COMMENT ON TABLE performance_metrics IS 'Real-time performance metrics for system monitoring';
COMMENT ON TABLE performance_alerts IS 'Performance alerts and notifications';
COMMENT ON TABLE benchmark_results IS 'Performance benchmark test results';
COMMENT ON TABLE capacity_alerts IS 'Capacity planning alerts and warnings';
COMMENT ON TABLE capacity_forecasts IS 'Predictive capacity forecasts';
COMMENT ON TABLE scaling_recommendations IS 'Automated scaling recommendations';