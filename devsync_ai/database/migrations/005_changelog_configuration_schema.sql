-- Migration: Changelog Configuration Management Schema
-- Version: 005
-- Description: Create tables for changelog configuration management with versioning and templates

-- Global changelog configuration table
CREATE TABLE IF NOT EXISTS changelog_global_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment VARCHAR(50) NOT NULL,
    configuration JSONB NOT NULL,
    version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(environment)
);

-- Team-specific changelog configurations
CREATE TABLE IF NOT EXISTS changelog_team_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id VARCHAR(100) NOT NULL,
    team_name VARCHAR(200),
    configuration JSONB NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_generated TIMESTAMP,
    generation_count INTEGER DEFAULT 0,
    UNIQUE(team_id)
);

-- Configuration version history for rollback support
CREATE TABLE IF NOT EXISTS changelog_config_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id VARCHAR(100) NOT NULL,
    team_id VARCHAR(100) NOT NULL,
    config_hash VARCHAR(64) NOT NULL,
    configuration JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT FALSE,
    rollback_available BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    UNIQUE(version_id)
);

-- Configuration templates for guided setup
CREATE TABLE IF NOT EXISTS changelog_config_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL, -- e.g., 'engineering', 'product', 'qa'
    template_config JSONB NOT NULL,
    setup_wizard_steps JSONB DEFAULT '[]',
    validation_rules JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    usage_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    UNIQUE(template_id)
);

-- Configuration change audit log
CREATE TABLE IF NOT EXISTS changelog_config_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id VARCHAR(100),
    action VARCHAR(50) NOT NULL, -- 'create', 'update', 'delete', 'rollback'
    changed_by VARCHAR(100) NOT NULL,
    changed_at TIMESTAMP DEFAULT NOW(),
    old_config JSONB,
    new_config JSONB,
    change_summary TEXT,
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Configuration backup and restore tracking
CREATE TABLE IF NOT EXISTS changelog_config_backups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backup_id VARCHAR(100) NOT NULL,
    team_id VARCHAR(100),
    backup_type VARCHAR(50) NOT NULL, -- 'manual', 'automatic', 'pre_update'
    configuration JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100) NOT NULL,
    description TEXT,
    restore_count INTEGER DEFAULT 0,
    last_restored TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    UNIQUE(backup_id)
);

-- Configuration validation results
CREATE TABLE IF NOT EXISTS changelog_config_validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id VARCHAR(100) NOT NULL,
    validation_type VARCHAR(50) NOT NULL, -- 'save', 'import', 'scheduled'
    is_valid BOOLEAN NOT NULL,
    errors JSONB DEFAULT '[]',
    warnings JSONB DEFAULT '[]',
    suggestions JSONB DEFAULT '[]',
    validated_at TIMESTAMP DEFAULT NOW(),
    config_hash VARCHAR(64),
    metadata JSONB DEFAULT '{}'
);

-- Runtime configuration overrides
CREATE TABLE IF NOT EXISTS changelog_config_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id VARCHAR(100) NOT NULL,
    override_key VARCHAR(200) NOT NULL,
    override_value JSONB NOT NULL,
    override_type VARCHAR(50) NOT NULL, -- 'temporary', 'permanent', 'scheduled'
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    created_by VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    UNIQUE(team_id, override_key)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_changelog_team_configs_team_id ON changelog_team_configs(team_id);
CREATE INDEX IF NOT EXISTS idx_changelog_team_configs_enabled ON changelog_team_configs(enabled);
CREATE INDEX IF NOT EXISTS idx_changelog_team_configs_updated_at ON changelog_team_configs(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_changelog_config_versions_team_id ON changelog_config_versions(team_id);
CREATE INDEX IF NOT EXISTS idx_changelog_config_versions_created_at ON changelog_config_versions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_changelog_config_versions_is_active ON changelog_config_versions(is_active);

CREATE INDEX IF NOT EXISTS idx_changelog_config_templates_category ON changelog_config_templates(category);
CREATE INDEX IF NOT EXISTS idx_changelog_config_templates_is_active ON changelog_config_templates(is_active);

CREATE INDEX IF NOT EXISTS idx_changelog_config_audit_team_id ON changelog_config_audit(team_id);
CREATE INDEX IF NOT EXISTS idx_changelog_config_audit_changed_at ON changelog_config_audit(changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_changelog_config_audit_action ON changelog_config_audit(action);

CREATE INDEX IF NOT EXISTS idx_changelog_config_backups_team_id ON changelog_config_backups(team_id);
CREATE INDEX IF NOT EXISTS idx_changelog_config_backups_created_at ON changelog_config_backups(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_changelog_config_validations_team_id ON changelog_config_validations(team_id);
CREATE INDEX IF NOT EXISTS idx_changelog_config_validations_validated_at ON changelog_config_validations(validated_at DESC);

CREATE INDEX IF NOT EXISTS idx_changelog_config_overrides_team_id ON changelog_config_overrides(team_id);
CREATE INDEX IF NOT EXISTS idx_changelog_config_overrides_is_active ON changelog_config_overrides(is_active);
CREATE INDEX IF NOT EXISTS idx_changelog_config_overrides_expires_at ON changelog_config_overrides(expires_at);

-- Add RLS (Row Level Security) policies for team isolation
ALTER TABLE changelog_team_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE changelog_config_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE changelog_config_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE changelog_config_backups ENABLE ROW LEVEL SECURITY;
ALTER TABLE changelog_config_validations ENABLE ROW LEVEL SECURITY;
ALTER TABLE changelog_config_overrides ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (these would be customized based on your auth system)
-- Example policies - adjust based on your authentication system

-- Policy for team configs - users can only access their team's config
CREATE POLICY changelog_team_configs_policy ON changelog_team_configs
    FOR ALL USING (
        team_id = current_setting('app.current_team_id', true)
        OR current_setting('app.user_role', true) = 'admin'
    );

-- Policy for config versions - users can only access their team's versions
CREATE POLICY changelog_config_versions_policy ON changelog_config_versions
    FOR ALL USING (
        team_id = current_setting('app.current_team_id', true)
        OR current_setting('app.user_role', true) = 'admin'
    );

-- Policy for audit log - users can only see their team's audit entries
CREATE POLICY changelog_config_audit_policy ON changelog_config_audit
    FOR SELECT USING (
        team_id = current_setting('app.current_team_id', true)
        OR current_setting('app.user_role', true) = 'admin'
    );

-- Policy for backups - users can only access their team's backups
CREATE POLICY changelog_config_backups_policy ON changelog_config_backups
    FOR ALL USING (
        team_id = current_setting('app.current_team_id', true)
        OR current_setting('app.user_role', true) = 'admin'
    );

-- Policy for validations - users can only see their team's validation results
CREATE POLICY changelog_config_validations_policy ON changelog_config_validations
    FOR SELECT USING (
        team_id = current_setting('app.current_team_id', true)
        OR current_setting('app.user_role', true) = 'admin'
    );

-- Policy for overrides - users can only access their team's overrides
CREATE POLICY changelog_config_overrides_policy ON changelog_config_overrides
    FOR ALL USING (
        team_id = current_setting('app.current_team_id', true)
        OR current_setting('app.user_role', true) = 'admin'
    );

-- Create functions for configuration management

-- Function to automatically create config versions before updates
CREATE OR REPLACE FUNCTION create_config_version_before_update()
RETURNS TRIGGER AS $$
BEGIN
    -- Only create version if configuration actually changed
    IF OLD.configuration IS DISTINCT FROM NEW.configuration THEN
        INSERT INTO changelog_config_versions (
            version_id,
            team_id,
            config_hash,
            configuration,
            created_by,
            description,
            is_active
        ) VALUES (
            NEW.team_id || '_' || to_char(NOW(), 'YYYYMMDD_HH24MISS'),
            NEW.team_id,
            encode(sha256(OLD.configuration::text::bytea), 'hex'),
            OLD.configuration,
            coalesce(current_setting('app.current_user', true), 'system'),
            'Automatic version before update',
            FALSE
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic versioning
CREATE TRIGGER changelog_config_version_trigger
    BEFORE UPDATE ON changelog_team_configs
    FOR EACH ROW
    EXECUTE FUNCTION create_config_version_before_update();

-- Function to log configuration changes
CREATE OR REPLACE FUNCTION log_config_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO changelog_config_audit (
            team_id,
            action,
            changed_by,
            new_config,
            change_summary
        ) VALUES (
            NEW.team_id,
            'create',
            coalesce(current_setting('app.current_user', true), 'system'),
            NEW.configuration,
            'Configuration created'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO changelog_config_audit (
            team_id,
            action,
            changed_by,
            old_config,
            new_config,
            change_summary
        ) VALUES (
            NEW.team_id,
            'update',
            coalesce(current_setting('app.current_user', true), 'system'),
            OLD.configuration,
            NEW.configuration,
            'Configuration updated'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO changelog_config_audit (
            team_id,
            action,
            changed_by,
            old_config,
            change_summary
        ) VALUES (
            OLD.team_id,
            'delete',
            coalesce(current_setting('app.current_user', true), 'system'),
            OLD.configuration,
            'Configuration deleted'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for audit logging
CREATE TRIGGER changelog_config_audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON changelog_team_configs
    FOR EACH ROW
    EXECUTE FUNCTION log_config_change();

-- Function to clean up old versions (keep last 10 versions per team)
CREATE OR REPLACE FUNCTION cleanup_old_config_versions()
RETURNS void AS $$
BEGIN
    WITH ranked_versions AS (
        SELECT id,
               ROW_NUMBER() OVER (PARTITION BY team_id ORDER BY created_at DESC) as rn
        FROM changelog_config_versions
        WHERE rollback_available = TRUE
    )
    UPDATE changelog_config_versions 
    SET rollback_available = FALSE
    WHERE id IN (
        SELECT id FROM ranked_versions WHERE rn > 10
    );
END;
$$ LANGUAGE plpgsql;

-- Function to validate configuration JSON structure
CREATE OR REPLACE FUNCTION validate_changelog_config(config_json JSONB)
RETURNS BOOLEAN AS $$
BEGIN
    -- Basic validation - ensure required fields exist
    IF NOT (config_json ? 'team_id' AND config_json ? 'team_name') THEN
        RETURN FALSE;
    END IF;
    
    -- Validate schedule if present
    IF config_json ? 'schedule' THEN
        IF NOT (config_json->'schedule' ? 'day' AND config_json->'schedule' ? 'time') THEN
            RETURN FALSE;
        END IF;
    END IF;
    
    -- Validate distribution if present
    IF config_json ? 'distribution' THEN
        IF NOT (config_json->'distribution' ? 'primary_channel') THEN
            RETURN FALSE;
        END IF;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Add constraint to validate configuration structure
ALTER TABLE changelog_team_configs 
ADD CONSTRAINT valid_configuration_structure 
CHECK (validate_changelog_config(configuration));

-- Insert default configuration templates
INSERT INTO changelog_config_templates (
    template_id,
    name,
    description,
    category,
    template_config,
    setup_wizard_steps,
    validation_rules
) VALUES 
(
    'engineering_default',
    'Engineering Team Default',
    'Default configuration for engineering teams with technical focus',
    'engineering',
    '{
        "team_id": "engineering",
        "team_name": "Engineering Team",
        "enabled": true,
        "version": "1.0.0",
        "schedule": {
            "enabled": true,
            "day": "friday",
            "time": "16:00",
            "timezone": "UTC"
        },
        "data_sources": {
            "github": {"enabled": true, "analysis_depth": "comprehensive"},
            "jira": {"enabled": true, "analysis_depth": "comprehensive"},
            "team_metrics": {"enabled": true}
        },
        "content": {
            "template_style": "technical",
            "audience_type": "technical",
            "include_metrics": true,
            "include_contributor_recognition": true,
            "include_risk_analysis": true,
            "max_commits_displayed": 20,
            "max_tickets_displayed": 15
        },
        "distribution": {
            "primary_channel": "#engineering-updates",
            "secondary_channels": ["#general"],
            "export_formats": ["slack", "markdown"]
        },
        "interactive": {
            "enable_feedback_buttons": true,
            "enable_drill_down": true,
            "enable_export_options": true
        },
        "notifications": {
            "notify_on_generation": true,
            "notify_on_failure": true,
            "escalation_channels": ["#alerts"]
        }
    }'::jsonb,
    '[
        {
            "step": 1,
            "title": "Team Information",
            "description": "Configure basic team information",
            "fields": ["team_id", "team_name"]
        },
        {
            "step": 2,
            "title": "Schedule Setup",
            "description": "Configure when changelogs are generated",
            "fields": ["schedule.day", "schedule.time", "schedule.timezone"]
        },
        {
            "step": 3,
            "title": "Data Sources",
            "description": "Choose which data sources to include",
            "fields": ["data_sources.github.enabled", "data_sources.jira.enabled", "data_sources.team_metrics.enabled"]
        },
        {
            "step": 4,
            "title": "Distribution Channels",
            "description": "Configure where changelogs are sent",
            "fields": ["distribution.primary_channel", "distribution.secondary_channels"]
        }
    ]'::jsonb,
    '[
        {
            "rule": "required_fields",
            "fields": ["team_id", "team_name", "distribution.primary_channel"]
        },
        {
            "rule": "channel_format",
            "field": "distribution.primary_channel",
            "pattern": "^#.*"
        }
    ]'::jsonb
),
(
    'product_default',
    'Product Team Default',
    'Default configuration for product teams with business focus',
    'product',
    '{
        "team_id": "product",
        "team_name": "Product Team",
        "enabled": true,
        "version": "1.0.0",
        "schedule": {
            "enabled": true,
            "day": "thursday",
            "time": "15:00",
            "timezone": "UTC"
        },
        "data_sources": {
            "github": {"enabled": false},
            "jira": {"enabled": true, "analysis_depth": "standard"},
            "team_metrics": {"enabled": true}
        },
        "content": {
            "template_style": "professional",
            "audience_type": "business",
            "include_metrics": false,
            "include_contributor_recognition": false,
            "include_risk_analysis": true,
            "focus_areas": ["deliverables", "milestones"]
        },
        "distribution": {
            "primary_channel": "#product-updates",
            "secondary_channels": ["#stakeholders"],
            "export_formats": ["slack", "email"]
        },
        "interactive": {
            "enable_feedback_buttons": true,
            "enable_drill_down": false
        },
        "notifications": {
            "notify_on_generation": true,
            "notify_on_failure": true
        }
    }'::jsonb,
    '[
        {
            "step": 1,
            "title": "Team Information",
            "description": "Configure basic team information",
            "fields": ["team_id", "team_name"]
        },
        {
            "step": 2,
            "title": "Schedule Setup",
            "description": "Configure when changelogs are generated",
            "fields": ["schedule.day", "schedule.time", "schedule.timezone"]
        },
        {
            "step": 3,
            "title": "Content Focus",
            "description": "Configure what to include in changelogs",
            "fields": ["content.template_style", "content.audience_type", "content.focus_areas"]
        },
        {
            "step": 4,
            "title": "Distribution Channels",
            "description": "Configure where changelogs are sent",
            "fields": ["distribution.primary_channel", "distribution.secondary_channels"]
        }
    ]'::jsonb,
    '[
        {
            "rule": "required_fields",
            "fields": ["team_id", "team_name", "distribution.primary_channel"]
        }
    ]'::jsonb
);

-- Create view for active team configurations with metadata
CREATE OR REPLACE VIEW changelog_team_configs_view AS
SELECT 
    ctc.*,
    ccv.version_id as current_version_id,
    ccv.created_at as version_created_at,
    (
        SELECT COUNT(*) 
        FROM changelog_config_versions 
        WHERE team_id = ctc.team_id
    ) as version_count,
    (
        SELECT MAX(validated_at) 
        FROM changelog_config_validations 
        WHERE team_id = ctc.team_id AND is_valid = true
    ) as last_valid_validation,
    (
        SELECT COUNT(*) 
        FROM changelog_config_overrides 
        WHERE team_id = ctc.team_id AND is_active = true
    ) as active_overrides_count
FROM changelog_team_configs ctc
LEFT JOIN changelog_config_versions ccv ON ctc.team_id = ccv.team_id AND ccv.is_active = true
WHERE ctc.enabled = true;

-- Grant appropriate permissions (adjust based on your role system)
-- GRANT SELECT, INSERT, UPDATE ON changelog_team_configs TO changelog_user;
-- GRANT SELECT ON changelog_config_templates TO changelog_user;
-- GRANT SELECT ON changelog_config_versions TO changelog_user;
-- GRANT INSERT ON changelog_config_audit TO changelog_user;

COMMENT ON TABLE changelog_global_config IS 'Global changelog system configuration';
COMMENT ON TABLE changelog_team_configs IS 'Team-specific changelog configurations';
COMMENT ON TABLE changelog_config_versions IS 'Configuration version history for rollback support';
COMMENT ON TABLE changelog_config_templates IS 'Configuration templates for guided setup';
COMMENT ON TABLE changelog_config_audit IS 'Audit log for configuration changes';
COMMENT ON TABLE changelog_config_backups IS 'Configuration backup and restore tracking';
COMMENT ON TABLE changelog_config_validations IS 'Configuration validation results';
COMMENT ON TABLE changelog_config_overrides IS 'Runtime configuration overrides';