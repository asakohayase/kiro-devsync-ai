-- Initial database schema for DevSync AI
-- This migration creates all the core tables needed for the application

-- Enable UUID extension for generating UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Pull Requests tracking table
CREATE TABLE IF NOT EXISTS pull_requests (
    id TEXT PRIMARY KEY,
    repository TEXT NOT NULL,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open', 'draft', 'ready_for_review', 'merged', 'closed')),
    merge_conflicts BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    reviewers JSONB DEFAULT '[]'::jsonb,
    labels JSONB DEFAULT '[]'::jsonb,
    data JSONB, -- Full PR data from GitHub API
    
    -- Constraints
    CONSTRAINT valid_updated_at CHECK (updated_at >= created_at),
    CONSTRAINT valid_repository_format CHECK (repository ~ '^[^/]+/[^/]+$')
);

-- Create indexes for pull_requests
CREATE INDEX IF NOT EXISTS idx_pull_requests_repository ON pull_requests(repository);
CREATE INDEX IF NOT EXISTS idx_pull_requests_author ON pull_requests(author);
CREATE INDEX IF NOT EXISTS idx_pull_requests_status ON pull_requests(status);
CREATE INDEX IF NOT EXISTS idx_pull_requests_created_at ON pull_requests(created_at);
CREATE INDEX IF NOT EXISTS idx_pull_requests_updated_at ON pull_requests(updated_at);

-- JIRA tickets tracking table
CREATE TABLE IF NOT EXISTS jira_tickets (
    key TEXT PRIMARY KEY,
    summary TEXT NOT NULL,
    status TEXT NOT NULL,
    assignee TEXT,
    priority TEXT NOT NULL,
    story_points INTEGER CHECK (story_points >= 0),
    sprint TEXT,
    blocked BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL,
    time_in_status_seconds BIGINT DEFAULT 0,
    data JSONB, -- Full ticket data from JIRA API
    
    -- Constraints
    CONSTRAINT valid_jira_key_format CHECK (key ~ '^[A-Z]+-[0-9]+$'),
    CONSTRAINT valid_story_points CHECK (story_points IS NULL OR story_points >= 0)
);

-- Create indexes for jira_tickets
CREATE INDEX IF NOT EXISTS idx_jira_tickets_status ON jira_tickets(status);
CREATE INDEX IF NOT EXISTS idx_jira_tickets_assignee ON jira_tickets(assignee);
CREATE INDEX IF NOT EXISTS idx_jira_tickets_priority ON jira_tickets(priority);
CREATE INDEX IF NOT EXISTS idx_jira_tickets_sprint ON jira_tickets(sprint);
CREATE INDEX IF NOT EXISTS idx_jira_tickets_blocked ON jira_tickets(blocked);
CREATE INDEX IF NOT EXISTS idx_jira_tickets_last_updated ON jira_tickets(last_updated);

-- Team members table
CREATE TABLE IF NOT EXISTS team_members (
    username TEXT PRIMARY KEY,
    github_handle TEXT NOT NULL UNIQUE,
    jira_account TEXT NOT NULL UNIQUE,
    slack_user_id TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_username CHECK (username != ''),
    CONSTRAINT valid_github_handle CHECK (github_handle != ''),
    CONSTRAINT valid_jira_account CHECK (jira_account != ''),
    CONSTRAINT valid_slack_user_id CHECK (slack_user_id != ''),
    CONSTRAINT valid_role CHECK (role != '')
);

-- Create indexes for team_members
CREATE INDEX IF NOT EXISTS idx_team_members_github_handle ON team_members(github_handle);
CREATE INDEX IF NOT EXISTS idx_team_members_jira_account ON team_members(jira_account);
CREATE INDEX IF NOT EXISTS idx_team_members_slack_user_id ON team_members(slack_user_id);
CREATE INDEX IF NOT EXISTS idx_team_members_active ON team_members(active);

-- Bottlenecks tracking table
CREATE TABLE IF NOT EXISTS bottlenecks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type TEXT NOT NULL CHECK (type IN ('pr_review', 'ticket_blocked', 'inactive_member')),
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    description TEXT NOT NULL,
    affected_items JSONB DEFAULT '[]'::jsonb,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT valid_description CHECK (description != ''),
    CONSTRAINT valid_resolved_at CHECK (
        (resolved = FALSE AND resolved_at IS NULL) OR 
        (resolved = TRUE AND resolved_at IS NOT NULL)
    )
);

-- Create indexes for bottlenecks
CREATE INDEX IF NOT EXISTS idx_bottlenecks_type ON bottlenecks(type);
CREATE INDEX IF NOT EXISTS idx_bottlenecks_severity ON bottlenecks(severity);
CREATE INDEX IF NOT EXISTS idx_bottlenecks_detected_at ON bottlenecks(detected_at);
CREATE INDEX IF NOT EXISTS idx_bottlenecks_resolved ON bottlenecks(resolved);
CREATE INDEX IF NOT EXISTS idx_bottlenecks_resolved_at ON bottlenecks(resolved_at);

-- Slack messages history table
CREATE TABLE IF NOT EXISTS slack_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel TEXT NOT NULL,
    message_type TEXT NOT NULL CHECK (message_type IN ('standup', 'notification', 'changelog')),
    content TEXT NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    thread_ts TEXT,
    
    -- Constraints
    CONSTRAINT valid_channel CHECK (channel != ''),
    CONSTRAINT valid_content CHECK (content != '')
);

-- Create indexes for slack_messages
CREATE INDEX IF NOT EXISTS idx_slack_messages_channel ON slack_messages(channel);
CREATE INDEX IF NOT EXISTS idx_slack_messages_type ON slack_messages(message_type);
CREATE INDEX IF NOT EXISTS idx_slack_messages_sent_at ON slack_messages(sent_at);
CREATE INDEX IF NOT EXISTS idx_slack_messages_thread_ts ON slack_messages(thread_ts);

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at for team_members
CREATE TRIGGER update_team_members_updated_at 
    BEFORE UPDATE ON team_members 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments to tables for documentation
COMMENT ON TABLE pull_requests IS 'Tracks GitHub pull requests and their status';
COMMENT ON TABLE jira_tickets IS 'Tracks JIRA tickets and their progress';
COMMENT ON TABLE team_members IS 'Stores team member information and account mappings';
COMMENT ON TABLE bottlenecks IS 'Records detected workflow bottlenecks and their resolution';
COMMENT ON TABLE slack_messages IS 'Audit log of all Slack messages sent by the system';

-- Add comments to important columns
COMMENT ON COLUMN pull_requests.data IS 'Full GitHub API response data for the pull request';
COMMENT ON COLUMN jira_tickets.data IS 'Full JIRA API response data for the ticket';
COMMENT ON COLUMN jira_tickets.time_in_status_seconds IS 'Duration in seconds the ticket has been in current status';
COMMENT ON COLUMN bottlenecks.affected_items IS 'Array of IDs/keys of items affected by this bottleneck';
COMMENT ON COLUMN slack_messages.thread_ts IS 'Slack thread timestamp for threaded messages';