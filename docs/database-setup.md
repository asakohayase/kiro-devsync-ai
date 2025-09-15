# Database Setup Guide

This guide explains how to set up the Supabase database for DevSync AI.

## Prerequisites

- A Supabase account (sign up at https://supabase.com)
- Access to create a new project

## Step 1: Create a Supabase Project

1. Log into your Supabase dashboard at https://app.supabase.com
2. Click "New Project"
3. Choose your organization
4. Enter a project name (e.g., "devsync-ai")
5. Enter a secure database password
6. Select a region close to your deployment location
7. Click "Create new project"

## Step 2: Get Your Connection Credentials

Once your project is created, you'll need two pieces of information:

### Supabase URL
1. Go to your project dashboard
2. Click on "Settings" in the sidebar
3. Click on "API"
4. Copy the "Project URL" (it looks like `https://your-project-id.supabase.co`)

### Supabase Anon Key
1. In the same API settings page
2. Copy the "anon public" key from the "Project API keys" section
3. This is a long string starting with `eyJ...`

## Step 3: Configure Environment Variables

1. Copy the `.env.example` file to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and update the Supabase configuration:
   ```env
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

## Step 4: Run Database Migrations

1. Generate the combined migration script:
   ```bash
   uv run python -m devsync_ai.database.migrations.runner
   ```

2. This will create a file at `devsync_ai/database/migrations/run_migrations.sql`

3. Execute the migration in Supabase:
   - Go to your Supabase dashboard
   - Click on "SQL Editor" in the sidebar
   - Click "New query"
   - Copy the entire content of `run_migrations.sql`
   - Paste it into the SQL Editor
   - Click "Run" to execute the migration

## Step 5: Verify the Setup

1. Check that all tables were created:
   - Go to "Table Editor" in your Supabase dashboard
   - You should see tables: `pull_requests`, `jira_tickets`, `team_members`, `bottlenecks`, `slack_messages`

2. Test the database connection:
   ```bash
   uv run python -c "
   import asyncio
   from devsync_ai.database.connection import get_database
   
   async def test_connection():
       db = await get_database()
       healthy = await db.health_check()
       print(f'Database connection: {'✓ Healthy' if healthy else '✗ Failed'}')
   
   asyncio.run(test_connection())
   "
   ```

## Database Schema Overview

The migration creates the following tables:

### `pull_requests`
- Tracks GitHub pull requests
- Stores PR metadata, status, and review information
- Includes merge conflict detection

### `jira_tickets`
- Tracks JIRA tickets and their progress
- Stores ticket status, assignee, and story points
- Includes blocked ticket tracking

### `team_members`
- Maps team members across GitHub, JIRA, and Slack
- Stores roles and active status
- Enables cross-platform user identification

### `bottlenecks`
- Records detected workflow bottlenecks
- Categorizes by type and severity
- Tracks resolution status and timing

### `slack_messages`
- Audit log of all Slack messages sent by the system
- Supports threaded conversations
- Categorizes message types (standup, notification, changelog)

## Security Notes

- **Never commit your `.env` file** - it contains sensitive credentials
- The anon key is safe to use in client-side code, but keep it secure
- For production, consider using Supabase's service role key for server-side operations
- Enable Row Level Security (RLS) policies if you plan to have multiple tenants

## Troubleshooting

### Connection Issues
- Verify your `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are correct
- Check that your Supabase project is active (not paused)
- Ensure your network can reach supabase.co

### Migration Issues
- Make sure you're using the SQL Editor in Supabase dashboard
- Check for any syntax errors in the migration output
- Verify you have the necessary permissions in your Supabase project

### Permission Issues
- Ensure you're using the correct API key for your use case
- Check Supabase's authentication and authorization settings
- Review any Row Level Security policies that might be blocking access

## Next Steps

After setting up the database:
1. Configure other external services (GitHub, JIRA, Slack)
2. Set up the FastAPI server
3. Configure the scheduler for automated tasks
4. Test the complete workflow end-to-end