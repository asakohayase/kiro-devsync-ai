-- Migration: Create notification system tables
-- Description: Creates tables for notification logging, scheduling, and analytics

-- Enable RLS (Row Level Security)
ALTER DATABASE postgres SET row_security = on;

-- Create notification_log table for duplicate prevention
CREATE TABLE IF NOT EXISTS notification_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    notification_hash VARCHAR(64) NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    channel VARCHAR(100),
    team_id VARCHAR(100),
    author VARCHAR(100),
    data JSONB,
    sent_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for notification_log
CREATE INDEX IF NOT EXISTS idx_notification_log_hash ON notification_log(notification_hash);
CREATE INDEX IF NOT EXISTS idx_notification_log_type ON notification_log(notification_type);
CREATE INDEX IF NOT EXISTS idx_notification_log_sent_at ON notification_log(sent_at);
CREATE INDEX IF NOT EXISTS idx_notification_log_team_id ON notification_log(team_id);
CREATE INDEX IF NOT EXISTS idx_notification_log_created_at ON notification_log(created_at);

-- Composite index for duplicate checking
CREATE INDEX IF NOT EXISTS idx_notification_log_dedup ON notification_log(notification_hash, notification_type, sent_at);

-- Create scheduled_notifications table for work hours scheduling
CREATE TABLE IF NOT EXISTS scheduled_notifications (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    notification_type VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    data JSONB NOT NULL,
    channel VARCHAR(100) NOT NULL,
    team_id VARCHAR(100) NOT NULL,
    author VARCHAR(100),
    scheduled_for TIMESTAMP WITH TIME ZONE NOT NULL,
    sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    retry_count INTEGER DEFAULT 0,
    last_error TEXT
);

-- Create indexes for scheduled_notifications
CREATE INDEX IF NOT EXISTS idx_scheduled_notifications_scheduled_for ON scheduled_notifications(scheduled_for);
CREATE INDEX IF NOT EXISTS idx_scheduled_notifications_sent ON scheduled_notifications(sent);
CREATE INDEX IF NOT EXISTS idx_scheduled_notifications_team_id ON scheduled_notifications(team_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_notifications_type ON scheduled_notifications(notification_type);
CREATE INDEX IF NOT EXISTS idx_scheduled_notifications_created_at ON scheduled_notifications(created_at);

-- Composite index for scheduler queries
CREATE INDEX IF NOT EXISTS idx_scheduled_notifications_pending ON scheduled_notifications(sent, scheduled_for) WHERE sent = FALSE;

-- Create notification_analytics table for monitoring and optimization
CREATE TABLE IF NOT EXISTS notification_analytics (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    notification_type VARCHAR(50) NOT NULL,
    channel VARCHAR(100) NOT NULL,
    team_id VARCHAR(100),
    urgency VARCHAR(20),
    filtered BOOLEAN DEFAULT FALSE,
    batched BOOLEAN DEFAULT FALSE,
    delayed BOOLEAN DEFAULT FALSE,
    duplicate_prevented BOOLEAN DEFAULT FALSE,
    processing_time_ms FLOAT,
    sent_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for notification_analytics
CREATE INDEX IF NOT EXISTS idx_notification_analytics_type ON notification_analytics(notification_type);
CREATE INDEX IF NOT EXISTS idx_notification_analytics_channel ON notification_analytics(channel);
CREATE INDEX IF NOT EXISTS idx_notification_analytics_team_id ON notification_analytics(team_id);
CREATE INDEX IF NOT EXISTS idx_notification_analytics_sent_at ON notification_analytics(sent_at);
CREATE INDEX IF NOT EXISTS idx_notification_analytics_created_at ON notification_analytics(created_at);

-- Composite indexes for analytics queries
CREATE INDEX IF NOT EXISTS idx_notification_analytics_hourly ON notification_analytics(DATE_TRUNC('hour', sent_at), notification_type);
CREATE INDEX IF NOT EXISTS idx_notification_analytics_daily ON notification_analytics(DATE_TRUNC('day', sent_at), team_id);

-- Create channel_routing_stats table for routing analytics
CREATE TABLE IF NOT EXISTS channel_routing_stats (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    channel VARCHAR(100) NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    team_id VARCHAR(100),
    urgency VARCHAR(20),
    routing_reason VARCHAR(50),
    hour_bucket TIMESTAMP WITH TIME ZONE NOT NULL, -- Truncated to hour
    message_count INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for channel_routing_stats
CREATE INDEX IF NOT EXISTS idx_channel_routing_stats_channel ON channel_routing_stats(channel);
CREATE INDEX IF NOT EXISTS idx_channel_routing_stats_hour ON channel_routing_stats(hour_bucket);
CREATE INDEX IF NOT EXISTS idx_channel_routing_stats_team ON channel_routing_stats(team_id);

-- Unique constraint for aggregation
CREATE UNIQUE INDEX IF NOT EXISTS idx_channel_routing_stats_unique 
ON channel_routing_stats(channel, notification_type, team_id, urgency, routing_reason, hour_bucket);

-- Create batch_processing_stats table for batch analytics
CREATE TABLE IF NOT EXISTS batch_processing_stats (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    channel VARCHAR(100) NOT NULL,
    batch_type VARCHAR(50) NOT NULL,
    batch_size INTEGER NOT NULL,
    processing_time_ms FLOAT,
    messages_sent INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    hour_bucket TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for batch_processing_stats
CREATE INDEX IF NOT EXISTS idx_batch_processing_stats_channel ON batch_processing_stats(channel);
CREATE INDEX IF NOT EXISTS idx_batch_processing_stats_hour ON batch_processing_stats(hour_bucket);
CREATE INDEX IF NOT EXISTS idx_batch_processing_stats_created_at ON batch_processing_stats(created_at);

-- Create RLS policies

-- notification_log policies
ALTER TABLE notification_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "notification_log_select_policy" ON notification_log
    FOR SELECT USING (true); -- Allow read access for deduplication

CREATE POLICY "notification_log_insert_policy" ON notification_log
    FOR INSERT WITH CHECK (true); -- Allow insert for logging

CREATE POLICY "notification_log_delete_policy" ON notification_log
    FOR DELETE USING (created_at < NOW() - INTERVAL '30 days'); -- Allow cleanup of old records

-- scheduled_notifications policies
ALTER TABLE scheduled_notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "scheduled_notifications_select_policy" ON scheduled_notifications
    FOR SELECT USING (true); -- Allow read access for scheduler

CREATE POLICY "scheduled_notifications_insert_policy" ON scheduled_notifications
    FOR INSERT WITH CHECK (true); -- Allow insert for scheduling

CREATE POLICY "scheduled_notifications_update_policy" ON scheduled_notifications
    FOR UPDATE USING (true); -- Allow update for marking as sent

CREATE POLICY "scheduled_notifications_delete_policy" ON scheduled_notifications
    FOR DELETE USING (sent = true AND sent_at < NOW() - INTERVAL '7 days'); -- Allow cleanup of sent notifications

-- notification_analytics policies
ALTER TABLE notification_analytics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "notification_analytics_select_policy" ON notification_analytics
    FOR SELECT USING (true); -- Allow read access for analytics

CREATE POLICY "notification_analytics_insert_policy" ON notification_analytics
    FOR INSERT WITH CHECK (true); -- Allow insert for analytics

CREATE POLICY "notification_analytics_delete_policy" ON notification_analytics
    FOR DELETE USING (created_at < NOW() - INTERVAL '90 days'); -- Allow cleanup of old analytics

-- channel_routing_stats policies
ALTER TABLE channel_routing_stats ENABLE ROW LEVEL SECURITY;

CREATE POLICY "channel_routing_stats_select_policy" ON channel_routing_stats
    FOR SELECT USING (true);

CREATE POLICY "channel_routing_stats_insert_policy" ON channel_routing_stats
    FOR INSERT WITH CHECK (true);

CREATE POLICY "channel_routing_stats_update_policy" ON channel_routing_stats
    FOR UPDATE USING (true);

CREATE POLICY "channel_routing_stats_delete_policy" ON channel_routing_stats
    FOR DELETE USING (created_at < NOW() - INTERVAL '90 days');

-- batch_processing_stats policies
ALTER TABLE batch_processing_stats ENABLE ROW LEVEL SECURITY;

CREATE POLICY "batch_processing_stats_select_policy" ON batch_processing_stats
    FOR SELECT USING (true);

CREATE POLICY "batch_processing_stats_insert_policy" ON batch_processing_stats
    FOR INSERT WITH CHECK (true);

CREATE POLICY "batch_processing_stats_delete_policy" ON batch_processing_stats
    FOR DELETE USING (created_at < NOW() - INTERVAL '90 days');

-- Create functions for analytics

-- Function to get notification statistics by hour
CREATE OR REPLACE FUNCTION get_notification_stats_by_hour(
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE
)
RETURNS TABLE (
    hour_bucket TIMESTAMP WITH TIME ZONE,
    notification_type VARCHAR(50),
    channel VARCHAR(100),
    total_count BIGINT,
    filtered_count BIGINT,
    batched_count BIGINT,
    delayed_count BIGINT,
    duplicate_prevented_count BIGINT,
    avg_processing_time_ms FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        DATE_TRUNC('hour', na.sent_at) as hour_bucket,
        na.notification_type,
        na.channel,
        COUNT(*) as total_count,
        COUNT(*) FILTER (WHERE na.filtered = true) as filtered_count,
        COUNT(*) FILTER (WHERE na.batched = true) as batched_count,
        COUNT(*) FILTER (WHERE na.delayed = true) as delayed_count,
        COUNT(*) FILTER (WHERE na.duplicate_prevented = true) as duplicate_prevented_count,
        AVG(na.processing_time_ms) as avg_processing_time_ms
    FROM notification_analytics na
    WHERE na.sent_at >= start_time AND na.sent_at <= end_time
    GROUP BY DATE_TRUNC('hour', na.sent_at), na.notification_type, na.channel
    ORDER BY hour_bucket DESC, total_count DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get channel routing effectiveness
CREATE OR REPLACE FUNCTION get_channel_routing_effectiveness(
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE
)
RETURNS TABLE (
    channel VARCHAR(100),
    total_messages BIGINT,
    routing_reasons JSONB,
    urgency_distribution JSONB,
    team_distribution JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        crs.channel,
        SUM(crs.message_count) as total_messages,
        jsonb_object_agg(crs.routing_reason, SUM(crs.message_count)) as routing_reasons,
        jsonb_object_agg(crs.urgency, SUM(crs.message_count)) as urgency_distribution,
        jsonb_object_agg(crs.team_id, SUM(crs.message_count)) as team_distribution
    FROM channel_routing_stats crs
    WHERE crs.hour_bucket >= start_time AND crs.hour_bucket <= end_time
    GROUP BY crs.channel
    ORDER BY total_messages DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up old records
CREATE OR REPLACE FUNCTION cleanup_old_notification_records()
RETURNS TABLE (
    table_name TEXT,
    records_deleted BIGINT
) AS $$
DECLARE
    deleted_count BIGINT;
BEGIN
    -- Clean notification_log (keep 30 days)
    DELETE FROM notification_log WHERE created_at < NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    table_name := 'notification_log';
    records_deleted := deleted_count;
    RETURN NEXT;
    
    -- Clean scheduled_notifications (keep sent notifications for 7 days)
    DELETE FROM scheduled_notifications WHERE sent = true AND sent_at < NOW() - INTERVAL '7 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    table_name := 'scheduled_notifications';
    records_deleted := deleted_count;
    RETURN NEXT;
    
    -- Clean notification_analytics (keep 90 days)
    DELETE FROM notification_analytics WHERE created_at < NOW() - INTERVAL '90 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    table_name := 'notification_analytics';
    records_deleted := deleted_count;
    RETURN NEXT;
    
    -- Clean channel_routing_stats (keep 90 days)
    DELETE FROM channel_routing_stats WHERE created_at < NOW() - INTERVAL '90 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    table_name := 'channel_routing_stats';
    records_deleted := deleted_count;
    RETURN NEXT;
    
    -- Clean batch_processing_stats (keep 90 days)
    DELETE FROM batch_processing_stats WHERE created_at < NOW() - INTERVAL '90 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    table_name := 'batch_processing_stats';
    records_deleted := deleted_count;
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Create a scheduled job to run cleanup (if pg_cron is available)
-- This would need to be run manually if pg_cron is not available:
-- SELECT cron.schedule('cleanup-notifications', '0 2 * * *', 'SELECT cleanup_old_notification_records();');

COMMENT ON TABLE notification_log IS 'Stores notification records for duplicate prevention';
COMMENT ON TABLE scheduled_notifications IS 'Stores notifications scheduled for later delivery';
COMMENT ON TABLE notification_analytics IS 'Stores analytics data for notification processing';
COMMENT ON TABLE channel_routing_stats IS 'Stores channel routing statistics';
COMMENT ON TABLE batch_processing_stats IS 'Stores batch processing performance statistics';

COMMENT ON FUNCTION get_notification_stats_by_hour IS 'Returns notification statistics aggregated by hour';
COMMENT ON FUNCTION get_channel_routing_effectiveness IS 'Returns channel routing effectiveness metrics';
COMMENT ON FUNCTION cleanup_old_notification_records IS 'Cleans up old notification records across all tables';