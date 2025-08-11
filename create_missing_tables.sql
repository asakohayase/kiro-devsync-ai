-- Missing tables for DevSync AI JIRA integration
-- Run this in your Supabase SQL Editor

-- First, run the main migrations if you haven't already
-- (Copy the content from devsync_ai/database/migrations/run_migrations.sql)

-- Then add this missing table for PR-JIRA mappings:

CREATE TABLE IF NOT EXISTS pr_ticket_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pr_number INTEGER NOT NULL,
    ticket_key TEXT NOT NULL,
    pr_url TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_pr_number UNIQUE (pr_number),
    CONSTRAINT unique_ticket_key UNIQUE (ticket_key),
    CONSTRAINT valid_pr_number CHECK (pr_number > 0),
    CONSTRAINT valid_ticket_key_format CHECK (ticket_key ~ '^[A-Z]+-[0-9]+$'),
    CONSTRAINT valid_pr_url CHECK (pr_url LIKE 'https://github.com/%')
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_pr_ticket_mappings_pr_number ON pr_ticket_mappings(pr_number);
CREATE INDEX IF NOT EXISTS idx_pr_ticket_mappings_ticket_key ON pr_ticket_mappings(ticket_key);
CREATE INDEX IF NOT EXISTS idx_pr_ticket_mappings_created_at ON pr_ticket_mappings(created_at);

-- Add comment
COMMENT ON TABLE pr_ticket_mappings IS 'Maps GitHub PRs to JIRA tickets for integration';

-- Verify tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('jira_tickets', 'pr_ticket_mappings', 'bottlenecks', 'pull_requests')
ORDER BY table_name;