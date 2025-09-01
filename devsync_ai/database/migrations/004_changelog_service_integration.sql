-- Migration: Changelog Service Integration Schema
-- Description: Extends existing schema with changelog service integration tables
-- Version: 004
-- Date: 2025-08-16

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create changelog service integration tables that extend existing schema

-- Changelog generation jobs table (extends existing job tracking patterns)
CREATE TABLE IF NOT EXISTS changelog_generation_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id VARCHAR(100) NOT NULL,
    job_type VARCHAR(50) NOT NULL DEFAULT 'scheduled' CHECK (job_type IN ('scheduled', 'manual', 'retry')),
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    week_start_date DATE NOT NULL,
    week_end_date DATE NOT NULL,
    
    -- Configuration and parameters
    generation_config JSONB NOT NULL DEFAULT '{}',
    data_sources JSONB NOT NULL DEFAULT '{}',
    
    -- Execution tracking
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    execution_time_ms BIGINT,
    
    -- Results and output
    changelog_id UUID REFERENCES changelog_entries(id) ON DELETE SET NULL,
    output_data JSONB,
    error_details TEXT,
    
    -- Metadata
    triggered_by VARCHAR(100),
    hook_execution_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_execution_time CHECK (
        (completed_at IS NULL AND execution_time_ms IS NULL) OR
        (completed_at IS NOT NULL AND execution_time_ms IS NOT NULL AND execution_time_ms >= 0)
    ),
    CONSTRAINT valid_completion_time CHECK (completed_at IS NULL OR completed_at >= started_at)
);

-- Service health monitoring table (extends existing monitoring patterns)
CREATE TABLE IF NOT EXISTS changelog_service_health (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_component VARCHAR(100) NOT NULL,
    health_status VARCHAR(50) NOT NULL CHECK (health_status IN ('healthy', 'degraded', 'unhealthy', 'unknown')),
    
    -- Health metrics
    response_time_ms FLOAT,
    success_rate FLOAT CHECK (success_rate >= 0 AND success_rate <= 1),
    error_count INTEGER DEFAULT 0,
    
    -- Component-specific data
    component_data JSONB DEFAULT '{}',
    
    -- Timestamps
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_healthy_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    check_details TEXT,
    metadata JSONB DEFAULT '{}'
);

-- API endpoint usage tracking (extends existing API patterns)
CREATE TABLE IF NOT EXISTS changelog_api_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint VARCHAR(200) NOT NULL,
    method VARCHAR(10) NOT NULL,
    team_id VARCHAR(100),
    
    -- Request details
    request_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    response_status INTEGER,
    response_time_ms FLOAT,
    
    -- Authentication and authorization
    user_id VARCHAR(100),
    api_key_id VARCHAR(100),
    
    -- Request/response data
    request_size_bytes INTEGER DEFAULT 0,
    response_size_bytes INTEGER DEFAULT 0,
    
    -- Error tracking
    error_message TEXT,
    error_code VARCHAR(50),
    
    -- Metadata
    user_agent TEXT,
    ip_address INET,
    metadata JSONB DEFAULT '{}'
);

-- Configuration change audit table (extends existing audit patterns)
CREATE TABLE IF NOT EXISTS changelog_config_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id VARCHAR(100) NOT NULL,
    config_type VARCHAR(100) NOT NULL,
    
    -- Change details
    action VARCHAR(50) NOT NULL CHECK (action IN ('create', 'update', 'delete', 'enable', 'disable')),
    old_config JSONB,
    new_config JSONB,
    
    -- Change metadata
    changed_by VARCHAR(100),
    change_reason TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Validation and rollback
    validation_status VARCHAR(50) DEFAULT 'pending',
    rollback_data JSONB,
    
    -- Metadata
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Performance indexes for changelog service integration
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_generation_jobs_team_status 
ON changelog_generation_jobs(team_id, status, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_generation_jobs_week 
ON changelog_generation_jobs(week_start_date, week_end_date);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_generation_jobs_hook 
ON changelog_generation_jobs(hook_execution_id) WHERE hook_execution_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_service_health_component 
ON changelog_service_health(service_component, checked_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_service_health_status 
ON changelog_service_health(health_status, checked_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_api_usage_endpoint 
ON changelog_api_usage(endpoint, request_timestamp DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_api_usage_team 
ON changelog_api_usage(team_id, request_timestamp DESC) WHERE team_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_api_usage_performance 
ON changelog_api_usage(response_time_ms, request_timestamp DESC) WHERE response_time_ms IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_config_audit_team 
ON changelog_config_audit(team_id, timestamp DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_config_audit_type 
ON changelog_config_audit(config_type, timestamp DESC);

-- Triggers for updated_at timestamps
CREATE TRIGGER update_changelog_generation_jobs_updated_at 
    BEFORE UPDATE ON changelog_generation_jobs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Views for common service integration queries

-- View for active changelog generation jobs
CREATE OR REPLACE VIEW active_changelog_jobs AS
SELECT 
    cgj.*,
    EXTRACT(EPOCH FROM (NOW() - cgj.started_at))/60 as running_minutes,
    ce.status as changelog_status,
    ce.published_at
FROM changelog_generation_jobs cgj
LEFT JOIN changelog_entries ce ON cgj.changelog_id = ce.id
WHERE cgj.status IN ('pending', 'running')
ORDER BY cgj.created_at DESC;

-- View for service health dashboard
CREATE OR REPLACE VIEW changelog_service_health_summary AS
SELECT 
    service_component,
    health_status,
    AVG(response_time_ms) as avg_response_time_ms,
    AVG(success_rate) as avg_success_rate,
    SUM(error_count) as total_errors,
    MAX(checked_at) as last_check,
    COUNT(*) as check_count
FROM changelog_service_health
WHERE checked_at >= NOW() - INTERVAL '24 hours'
GROUP BY service_component, health_status
ORDER BY service_component, health_status;

-- View for API usage analytics
CREATE OR REPLACE VIEW changelog_api_usage_summary AS
SELECT 
    endpoint,
    method,
    DATE_TRUNC('hour', request_timestamp) as hour,
    COUNT(*) as request_count,
    AVG(response_time_ms) as avg_response_time_ms,
    COUNT(*) FILTER (WHERE response_status >= 200 AND response_status < 300) as success_count,
    COUNT(*) FILTER (WHERE response_status >= 400) as error_count,
    AVG(request_size_bytes) as avg_request_size,
    AVG(response_size_bytes) as avg_response_size
FROM changelog_api_usage
WHERE request_timestamp >= NOW() - INTERVAL '7 days'
GROUP BY endpoint, method, DATE_TRUNC('hour', request_timestamp)
ORDER BY hour DESC, endpoint, method;

-- Functions for service integration

-- Function to create changelog generation job
CREATE OR REPLACE FUNCTION create_changelog_generation_job(
    p_team_id VARCHAR(100),
    p_job_type VARCHAR(50),
    p_week_start_date DATE,
    p_week_end_date DATE,
    p_generation_config JSONB DEFAULT '{}',
    p_triggered_by VARCHAR(100) DEFAULT NULL,
    p_hook_execution_id VARCHAR(255) DEFAULT NULL
)
RETURNS UUID AS $
DECLARE
    job_id UUID;
BEGIN
    INSERT INTO changelog_generation_jobs (
        team_id,
        job_type,
        week_start_date,
        week_end_date,
        generation_config,
        triggered_by,
        hook_execution_id
    ) VALUES (
        p_team_id,
        p_job_type,
        p_week_start_date,
        p_week_end_date,
        p_generation_config,
        p_triggered_by,
        p_hook_execution_id
    ) RETURNING id INTO job_id;
    
    RETURN job_id;
END;
$ LANGUAGE plpgsql;

-- Function to update job status
CREATE OR REPLACE FUNCTION update_changelog_job_status(
    p_job_id UUID,
    p_status VARCHAR(50),
    p_changelog_id UUID DEFAULT NULL,
    p_error_details TEXT DEFAULT NULL,
    p_output_data JSONB DEFAULT NULL
)
RETURNS BOOLEAN AS $
DECLARE
    execution_time BIGINT;
BEGIN
    -- Calculate execution time if completing
    IF p_status IN ('completed', 'failed', 'cancelled') THEN
        SELECT EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000
        INTO execution_time
        FROM changelog_generation_jobs
        WHERE id = p_job_id;
    END IF;
    
    UPDATE changelog_generation_jobs
    SET 
        status = p_status,
        completed_at = CASE WHEN p_status IN ('completed', 'failed', 'cancelled') THEN NOW() ELSE completed_at END,
        execution_time_ms = COALESCE(execution_time, execution_time_ms),
        changelog_id = COALESCE(p_changelog_id, changelog_id),
        error_details = COALESCE(p_error_details, error_details),
        output_data = COALESCE(p_output_data, output_data),
        updated_at = NOW()
    WHERE id = p_job_id;
    
    RETURN FOUND;
END;
$ LANGUAGE plpgsql;

-- Function to record service health check
CREATE OR REPLACE FUNCTION record_service_health_check(
    p_service_component VARCHAR(100),
    p_health_status VARCHAR(50),
    p_response_time_ms FLOAT DEFAULT NULL,
    p_success_rate FLOAT DEFAULT NULL,
    p_error_count INTEGER DEFAULT 0,
    p_component_data JSONB DEFAULT '{}',
    p_check_details TEXT DEFAULT NULL
)
RETURNS UUID AS $
DECLARE
    health_id UUID;
    last_healthy TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Update last_healthy_at if status is healthy
    IF p_health_status = 'healthy' THEN
        last_healthy := NOW();
    ELSE
        -- Get the last healthy timestamp for this component
        SELECT last_healthy_at INTO last_healthy
        FROM changelog_service_health
        WHERE service_component = p_service_component
        ORDER BY checked_at DESC
        LIMIT 1;
    END IF;
    
    INSERT INTO changelog_service_health (
        service_component,
        health_status,
        response_time_ms,
        success_rate,
        error_count,
        component_data,
        check_details,
        last_healthy_at
    ) VALUES (
        p_service_component,
        p_health_status,
        p_response_time_ms,
        p_success_rate,
        p_error_count,
        p_component_data,
        p_check_details,
        last_healthy
    ) RETURNING id INTO health_id;
    
    RETURN health_id;
END;
$ LANGUAGE plpgsql;

-- Function to record API usage
CREATE OR REPLACE FUNCTION record_api_usage(
    p_endpoint VARCHAR(200),
    p_method VARCHAR(10),
    p_team_id VARCHAR(100) DEFAULT NULL,
    p_response_status INTEGER DEFAULT NULL,
    p_response_time_ms FLOAT DEFAULT NULL,
    p_user_id VARCHAR(100) DEFAULT NULL,
    p_request_size_bytes INTEGER DEFAULT 0,
    p_response_size_bytes INTEGER DEFAULT 0,
    p_error_message TEXT DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'
)
RETURNS UUID AS $
DECLARE
    usage_id UUID;
BEGIN
    INSERT INTO changelog_api_usage (
        endpoint,
        method,
        team_id,
        response_status,
        response_time_ms,
        user_id,
        request_size_bytes,
        response_size_bytes,
        error_message,
        metadata
    ) VALUES (
        p_endpoint,
        p_method,
        p_team_id,
        p_response_status,
        p_response_time_ms,
        p_user_id,
        p_request_size_bytes,
        p_response_size_bytes,
        p_error_message,
        p_metadata
    ) RETURNING id INTO usage_id;
    
    RETURN usage_id;
END;
$ LANGUAGE plpgsql;

-- Function to audit configuration changes
CREATE OR REPLACE FUNCTION audit_config_change(
    p_team_id VARCHAR(100),
    p_config_type VARCHAR(100),
    p_action VARCHAR(50),
    p_old_config JSONB DEFAULT NULL,
    p_new_config JSONB DEFAULT NULL,
    p_changed_by VARCHAR(100) DEFAULT NULL,
    p_change_reason TEXT DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'
)
RETURNS UUID AS $
DECLARE
    audit_id UUID;
BEGIN
    INSERT INTO changelog_config_audit (
        team_id,
        config_type,
        action,
        old_config,
        new_config,
        changed_by,
        change_reason,
        metadata
    ) VALUES (
        p_team_id,
        p_config_type,
        p_action,
        p_old_config,
        p_new_config,
        p_changed_by,
        p_change_reason,
        p_metadata
    ) RETURNING id INTO audit_id;
    
    RETURN audit_id;
END;
$ LANGUAGE plpgsql;

-- Row Level Security policies for service integration tables
ALTER TABLE changelog_generation_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE changelog_service_health ENABLE ROW LEVEL SECURITY;
ALTER TABLE changelog_api_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE changelog_config_audit ENABLE ROW LEVEL SECURITY;

-- Team isolation policies
CREATE POLICY changelog_generation_jobs_team_isolation ON changelog_generation_jobs
    FOR ALL USING (team_id = current_setting('app.current_team_id', true));

CREATE POLICY changelog_api_usage_team_isolation ON changelog_api_usage
    FOR ALL USING (
        team_id IS NULL OR 
        team_id = current_setting('app.current_team_id', true)
    );

CREATE POLICY changelog_config_audit_team_isolation ON changelog_config_audit
    FOR ALL USING (team_id = current_setting('app.current_team_id', true));

-- Service health is accessible to all (for monitoring)
CREATE POLICY changelog_service_health_read_all ON changelog_service_health
    FOR SELECT USING (true);

-- Only service accounts can write health data
CREATE POLICY changelog_service_health_write_service ON changelog_service_health
    FOR INSERT WITH CHECK (current_setting('app.user_role', true) = 'service');

-- Comments for documentation
COMMENT ON TABLE changelog_generation_jobs IS 'Tracks changelog generation jobs and their execution status';
COMMENT ON TABLE changelog_service_health IS 'Monitors health status of changelog service components';
COMMENT ON TABLE changelog_api_usage IS 'Tracks API endpoint usage and performance metrics';
COMMENT ON TABLE changelog_config_audit IS 'Audits all configuration changes for compliance and rollback';

COMMENT ON FUNCTION create_changelog_generation_job IS 'Creates a new changelog generation job with proper tracking';
COMMENT ON FUNCTION update_changelog_job_status IS 'Updates job status and calculates execution metrics';
COMMENT ON FUNCTION record_service_health_check IS 'Records service health check results with historical tracking';
COMMENT ON FUNCTION record_api_usage IS 'Records API usage metrics for monitoring and analytics';
COMMENT ON FUNCTION audit_config_change IS 'Audits configuration changes for compliance and rollback capability';

-- Grant permissions for service integration
-- GRANT SELECT, INSERT, UPDATE ON changelog_generation_jobs TO changelog_service;
-- GRANT SELECT, INSERT ON changelog_service_health TO changelog_service;
-- GRANT SELECT, INSERT ON changelog_api_usage TO changelog_service;
-- GRANT SELECT, INSERT ON changelog_config_audit TO changelog_service;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO changelog_service;