-- Migration: Create team hook configurations table
-- Description: Creates table for storing team-specific hook configurations and rules

-- Create team_hook_configurations table
CREATE TABLE IF NOT EXISTS team_hook_configurations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    team_id VARCHAR(100) NOT NULL,
    configuration JSONB NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    version VARCHAR(50) DEFAULT '1.0.0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(team_id)
);

-- Create indexes for team_hook_configurations
CREATE INDEX IF NOT EXISTS idx_team_hook_configurations_team_id 
ON team_hook_configurations(team_id);

CREATE INDEX IF NOT EXISTS idx_team_hook_configurations_enabled 
ON team_hook_configurations(enabled);

CREATE INDEX IF NOT EXISTS idx_team_hook_configurations_updated_at 
ON team_hook_configurations(updated_at);

-- Create GIN index for JSONB configuration queries
CREATE INDEX IF NOT EXISTS idx_team_hook_configurations_config_gin 
ON team_hook_configurations USING GIN (configuration);

-- Enable RLS (Row Level Security)
ALTER TABLE team_hook_configurations ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "team_hook_configurations_select_policy" ON team_hook_configurations
    FOR SELECT USING (true);

CREATE POLICY "team_hook_configurations_insert_policy" ON team_hook_configurations
    FOR INSERT WITH CHECK (true);

CREATE POLICY "team_hook_configurations_update_policy" ON team_hook_configurations
    FOR UPDATE USING (true);

CREATE POLICY "team_hook_configurations_delete_policy" ON team_hook_configurations
    FOR DELETE USING (true);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_team_hook_configurations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update updated_at
CREATE TRIGGER trigger_update_team_hook_configurations_updated_at
    BEFORE UPDATE ON team_hook_configurations
    FOR EACH ROW
    EXECUTE FUNCTION update_team_hook_configurations_updated_at();

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

-- Function to search configurations by rule criteria
CREATE OR REPLACE FUNCTION search_team_configurations_by_rule(
    hook_type_param VARCHAR(100) DEFAULT NULL,
    channel_param VARCHAR(100) DEFAULT NULL,
    enabled_only BOOLEAN DEFAULT TRUE
)
RETURNS TABLE (
    team_id VARCHAR(100),
    team_name TEXT,
    matching_rules JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        thc.team_id,
        thc.configuration->>'team_name' as team_name,
        jsonb_agg(rule) as matching_rules
    FROM team_hook_configurations thc,
         jsonb_array_elements(thc.configuration->'rules') as rule
    WHERE (enabled_only = FALSE OR thc.enabled = TRUE)
        AND (hook_type_param IS NULL OR rule->'hook_types' ? hook_type_param)
        AND (channel_param IS NULL OR rule->'metadata'->'channels' ? channel_param)
        AND (rule->>'enabled')::boolean = TRUE
    GROUP BY thc.team_id, thc.configuration->>'team_name';
END;
$$ LANGUAGE plpgsql;

-- Function to get configuration statistics
CREATE OR REPLACE FUNCTION get_team_configuration_stats()
RETURNS TABLE (
    total_teams BIGINT,
    enabled_teams BIGINT,
    disabled_teams BIGINT,
    total_rules BIGINT,
    enabled_rules BIGINT,
    avg_rules_per_team NUMERIC,
    most_common_hook_types JSONB
) AS $$
DECLARE
    hook_type_counts JSONB;
BEGIN
    -- Get basic counts
    SELECT 
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE enabled = TRUE) as enabled,
        COUNT(*) FILTER (WHERE enabled = FALSE) as disabled
    INTO total_teams, enabled_teams, disabled_teams
    FROM team_hook_configurations;
    
    -- Get rule statistics
    SELECT 
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE (rule->>'enabled')::boolean = TRUE) as enabled,
        AVG(jsonb_array_length(configuration->'rules'))
    INTO total_rules, enabled_rules, avg_rules_per_team
    FROM team_hook_configurations thc,
         jsonb_array_elements(thc.configuration->'rules') as rule
    WHERE thc.enabled = TRUE;
    
    -- Get most common hook types
    SELECT jsonb_object_agg(hook_type, count)
    INTO hook_type_counts
    FROM (
        SELECT 
            hook_type.value as hook_type,
            COUNT(*) as count
        FROM team_hook_configurations thc,
             jsonb_array_elements(thc.configuration->'rules') as rule,
             jsonb_array_elements_text(rule->'hook_types') as hook_type
        WHERE thc.enabled = TRUE
            AND (rule->>'enabled')::boolean = TRUE
        GROUP BY hook_type.value
        ORDER BY COUNT(*) DESC
        LIMIT 10
    ) hook_counts;
    
    most_common_hook_types := COALESCE(hook_type_counts, '{}'::jsonb);
    
    RETURN QUERY SELECT 
        total_teams, enabled_teams, disabled_teams,
        total_rules, enabled_rules, avg_rules_per_team,
        most_common_hook_types;
END;
$$ LANGUAGE plpgsql;

-- Comments
COMMENT ON TABLE team_hook_configurations IS 'Team-specific hook configurations and rules';
COMMENT ON COLUMN team_hook_configurations.team_id IS 'Unique identifier for the team';
COMMENT ON COLUMN team_hook_configurations.configuration IS 'JSONB configuration containing rules, channels, and preferences';
COMMENT ON COLUMN team_hook_configurations.enabled IS 'Whether the team configuration is active';
COMMENT ON COLUMN team_hook_configurations.version IS 'Configuration schema version';

COMMENT ON FUNCTION get_team_hook_configuration IS 'Get team configuration with fallback to default';
COMMENT ON FUNCTION search_team_configurations_by_rule IS 'Search team configurations by rule criteria';
COMMENT ON FUNCTION get_team_configuration_stats IS 'Get statistics about team configurations';
COMMENT ON FUNCTION validate_team_hook_configuration IS 'Validate team configuration JSON structure';