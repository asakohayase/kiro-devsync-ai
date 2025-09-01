-- Migration: Changelog History Management Schema
-- Description: Create tables for comprehensive changelog history management
-- Version: 003
-- Date: 2025-01-16

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create enum types
CREATE TYPE changelog_status AS ENUM ('draft', 'published', 'archived', 'deleted');
CREATE TYPE export_format AS ENUM ('json', 'csv', 'pdf', 'html', 'markdown');
CREATE TYPE retention_action AS ENUM ('archive', 'delete', 'compress', 'migrate');

-- Main changelog entries table with versioning
CREATE TABLE IF NOT EXISTS changelog_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id VARCHAR(100) NOT NULL,
    week_start_date DATE NOT NULL,
    week_end_date DATE NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    status changelog_status NOT NULL DEFAULT 'draft',
    content JSONB NOT NULL,
    metadata JSONB,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    published_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(100),
    tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique versioning per team and week
    UNIQUE(team_id, week_start_date, version)
);

-- Audit trail table for change tracking
CREATE TABLE IF NOT EXISTS changelog_audit_trail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    changelog_id UUID NOT NULL REFERENCES changelog_entries(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    user_id VARCHAR(100),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    details JSONB,
    ip_address INET,
    user_agent TEXT
);

-- Distribution tracking table
CREATE TABLE IF NOT EXISTS changelog_distributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    changelog_id UUID NOT NULL REFERENCES changelog_entries(id) ON DELETE CASCADE,
    channel_type VARCHAR(50) NOT NULL,
    channel_identifier VARCHAR(200) NOT NULL,
    distribution_status VARCHAR(50) NOT NULL,
    delivered_at TIMESTAMP WITH TIME ZONE,
    engagement_metrics JSONB,
    error_details TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Analytics and metrics table
CREATE TABLE IF NOT EXISTS changelog_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    changelog_id UUID REFERENCES changelog_entries(id) ON DELETE CASCADE,
    team_id VARCHAR(100) NOT NULL,
    metric_type VARCHAR(100) NOT NULL,
    metric_value DECIMAL NOT NULL,
    metric_metadata JSONB,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Index for efficient metric queries
    INDEX idx_changelog_analytics_team_metric (team_id, metric_type, recorded_at)
);

-- Export jobs table
CREATE TABLE IF NOT EXISTS changelog_export_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    export_format export_format NOT NULL,
    filters JSONB NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    file_path TEXT,
    file_size BIGINT,
    record_count INTEGER DEFAULT 0,
    created_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    schedule_config JSONB
);

-- Retention policies table
CREATE TABLE IF NOT EXISTS changelog_retention_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id VARCHAR(100) NOT NULL UNIQUE,
    archive_after_days INTEGER NOT NULL DEFAULT 365,
    delete_after_days INTEGER NOT NULL DEFAULT 2555, -- 7 years
    compress_after_days INTEGER,
    legal_hold BOOLEAN DEFAULT FALSE,
    compliance_requirements TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Backup metadata table
CREATE TABLE IF NOT EXISTS changelog_backups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backup_id VARCHAR(100) NOT NULL UNIQUE,
    team_id VARCHAR(100),
    backup_path TEXT NOT NULL,
    file_size BIGINT,
    record_count INTEGER,
    validation_hash VARCHAR(64),
    status VARCHAR(50) NOT NULL DEFAULT 'created',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    validated_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB
);

-- Performance indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_entries_team_date 
ON changelog_entries(team_id, week_start_date DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_entries_status 
ON changelog_entries(status, generated_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_entries_created_by 
ON changelog_entries(created_by, generated_at DESC);

-- Full-text search index on content
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_entries_content_search 
ON changelog_entries USING GIN (to_tsvector('english', content::text));

-- Tags search index
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_entries_tags 
ON changelog_entries USING GIN (tags);

-- Audit trail indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_audit_trail_changelog 
ON changelog_audit_trail(changelog_id, timestamp DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_audit_trail_user 
ON changelog_audit_trail(user_id, timestamp DESC);

-- Distribution tracking indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_distributions_status 
ON changelog_distributions(distribution_status, delivered_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_distributions_changelog 
ON changelog_distributions(changelog_id, created_at DESC);

-- Analytics indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_changelog_analytics_team_date 
ON changelog_analytics(team_id, recorded_at DESC);

-- Triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_changelog_entries_updated_at 
    BEFORE UPDATE ON changelog_entries 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_changelog_retention_policies_updated_at 
    BEFORE UPDATE ON changelog_retention_policies 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to create changelog tables (for initialization)
CREATE OR REPLACE FUNCTION create_changelog_tables()
RETURNS VOID AS $$
BEGIN
    -- This function ensures all tables exist
    -- Tables are already created above, so this is a no-op
    -- but provides a consistent interface for initialization
    RAISE NOTICE 'Changelog tables initialized successfully';
END;
$$ LANGUAGE plpgsql;

-- Row Level Security (RLS) policies
ALTER TABLE changelog_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE changelog_audit_trail ENABLE ROW LEVEL SECURITY;
ALTER TABLE changelog_distributions ENABLE ROW LEVEL SECURITY;
ALTER TABLE changelog_analytics ENABLE ROW LEVEL SECURITY;

-- Basic RLS policy - teams can only access their own data
CREATE POLICY changelog_entries_team_isolation ON changelog_entries
    FOR ALL USING (team_id = current_setting('app.current_team_id', true));

CREATE POLICY changelog_audit_trail_access ON changelog_audit_trail
    FOR ALL USING (
        changelog_id IN (
            SELECT id FROM changelog_entries 
            WHERE team_id = current_setting('app.current_team_id', true)
        )
    );

CREATE POLICY changelog_distributions_access ON changelog_distributions
    FOR ALL USING (
        changelog_id IN (
            SELECT id FROM changelog_entries 
            WHERE team_id = current_setting('app.current_team_id', true)
        )
    );

CREATE POLICY changelog_analytics_team_isolation ON changelog_analytics
    FOR ALL USING (team_id = current_setting('app.current_team_id', true));

-- Views for common queries
CREATE OR REPLACE VIEW changelog_entries_with_stats AS
SELECT 
    ce.*,
    COUNT(cd.id) as distribution_count,
    COUNT(CASE WHEN cd.distribution_status = 'delivered' THEN 1 END) as successful_distributions,
    MAX(cd.delivered_at) as last_delivered_at,
    COUNT(cat.id) as audit_trail_count
FROM changelog_entries ce
LEFT JOIN changelog_distributions cd ON ce.id = cd.changelog_id
LEFT JOIN changelog_audit_trail cat ON ce.id = cat.changelog_id
GROUP BY ce.id;

-- View for team analytics
CREATE OR REPLACE VIEW team_changelog_analytics AS
SELECT 
    team_id,
    DATE_TRUNC('month', week_start_date) as month,
    COUNT(*) as total_changelogs,
    COUNT(CASE WHEN status = 'published' THEN 1 END) as published_changelogs,
    AVG(version) as avg_version,
    COUNT(DISTINCT created_by) as unique_contributors,
    AVG(EXTRACT(EPOCH FROM (published_at - generated_at))/3600) as avg_publish_delay_hours
FROM changelog_entries
WHERE status != 'deleted'
GROUP BY team_id, DATE_TRUNC('month', week_start_date);

-- Materialized view for performance metrics (refresh periodically)
CREATE MATERIALIZED VIEW IF NOT EXISTS changelog_performance_metrics AS
SELECT 
    team_id,
    DATE_TRUNC('week', recorded_at) as week,
    metric_type,
    AVG(metric_value) as avg_value,
    MIN(metric_value) as min_value,
    MAX(metric_value) as max_value,
    COUNT(*) as sample_count
FROM changelog_analytics
GROUP BY team_id, DATE_TRUNC('week', recorded_at), metric_type;

-- Index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_changelog_performance_metrics_unique
ON changelog_performance_metrics(team_id, week, metric_type);

-- Function to refresh performance metrics
CREATE OR REPLACE FUNCTION refresh_changelog_performance_metrics()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY changelog_performance_metrics;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE changelog_entries IS 'Main table storing changelog entries with versioning support';
COMMENT ON TABLE changelog_audit_trail IS 'Audit trail for all changelog operations';
COMMENT ON TABLE changelog_distributions IS 'Tracking of changelog distribution across channels';
COMMENT ON TABLE changelog_analytics IS 'Metrics and analytics data for changelogs';
COMMENT ON TABLE changelog_export_jobs IS 'Export job tracking and scheduling';
COMMENT ON TABLE changelog_retention_policies IS 'Data retention policies per team';
COMMENT ON TABLE changelog_backups IS 'Backup metadata and validation information';

COMMENT ON COLUMN changelog_entries.content IS 'JSONB content of the changelog with structured data';
COMMENT ON COLUMN changelog_entries.metadata IS 'Additional metadata for the changelog entry';
COMMENT ON COLUMN changelog_entries.tags IS 'Array of tags for categorization and search';
COMMENT ON COLUMN changelog_entries.version IS 'Version number for the same week/team combination';

-- Grant permissions (adjust based on your user roles)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO changelog_service;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO changelog_service;