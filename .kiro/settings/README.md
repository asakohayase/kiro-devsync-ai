# Kiro MCP Server Configuration

This directory contains the Model Context Protocol (MCP) server configuration for the DevSync AI project.

## Setup for Team Members

### 1. Set Up Environment Variables

Add these to your `.env` file:

```bash
# Supabase Configuration
SUPABASE_PROJECT_REF=your-supabase-project-ref-here
SUPABASE_ACCESS_TOKEN=your-personal-access-token-here
```

### 3. Get Your Supabase Personal Access Token

1. Go to [Supabase Dashboard → Account → Access Tokens](https://supabase.com/dashboard/account/tokens)
2. Create a new token (name it "Kiro MCP Server")
3. Copy the token and add it to your `.env` file

### 4. Atlassian MCP Setup

The Atlassian MCP server will prompt you for OAuth authentication on first use:
1. When you first use JIRA commands in Kiro, a browser window will open
2. Login with your Atlassian account
3. Grant permissions to the MCP server

## Available MCP Servers

### Supabase Server
- **Purpose**: Database operations and project management
- **Capabilities**: SQL queries, table operations, migrations, project info
- **Authentication**: Personal Access Token

### Atlassian Server  
- **Purpose**: JIRA and Confluence operations
- **Capabilities**: Ticket management, search, creation, status updates
- **Authentication**: OAuth 2.0 (browser-based)

## Usage Examples

Once configured, you can use natural language commands in Kiro:

### Supabase Operations
- "Show me all tables in the database"
- "Query the pr_ticket_mappings table"
- "Execute this SQL: SELECT * FROM slack_messages LIMIT 5"

### JIRA Operations
- "Show me all open tickets in project DP"
- "Update ticket DP-17 status to Done"
- "Create a new ticket titled 'Fix authentication bug'"

## Security Notes

- ✅ **Safe to commit**: `mcp.json` and this README (no secrets, only env var references)
- ❌ **Never commit**: Actual tokens in `.env` file
- ⚠️ **Project ref**: The Supabase project reference should be kept private to your team

## Troubleshooting

### Supabase MCP Issues
- Verify your Personal Access Token is valid
- Check that `SUPABASE_PROJECT_REF` matches your project
- Ensure you have proper permissions on the Supabase project

### Atlassian MCP Issues  
- Complete the OAuth flow in your browser
- Verify you have access to the JIRA project
- Check that your Atlassian account has proper permissions

### General MCP Issues
- Restart Kiro after configuration changes
- Check the MCP server status in Kiro's MCP panel
- Verify Node.js is installed (required for `npx` commands)