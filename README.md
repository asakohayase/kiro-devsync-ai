# DevSync AI

Smart release coordination tool that automates communication and coordination tasks within software teams by connecting GitHub, JIRA, and Slack.

## Features

- Automatic GitHub pull request tracking and status monitoring
- JIRA ticket synchronization and blocker detection
- Automated Slack notifications and daily standup summaries
- Weekly changelog generation from commit history
- Team analytics and bottleneck identification
- RESTful API for integration with other tools

## Quick Start

### Local Development

1. **Install uv (if not already installed):**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Set up the database:**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials (see docs/database-setup.md)
   
   # Run database migrations (see setup guide for details)
   uv run python -m devsync_ai.database.migrations.runner
   
   # Verify database connection
   uv run python scripts/check_database.py
   ```

4. **Configure other services:**
   ```bash
   # Edit .env with your GitHub, JIRA, and Slack API keys
   ```

5. **Run the application:**
   ```bash
   uv run python -m devsync_ai.main
   ```

6. **Access the API:**
   - API documentation: http://localhost:8000/docs
   - Health check: http://localhost:8000/api/v1/health

### Deployment on Render

1. **Connect your GitHub repository to Render**
2. **Create a new Web Service with these settings:**
   - **Build Command:** `uv sync`
   - **Start Command:** `uv run python -m devsync_ai.main`
   - **Environment:** Python 3.11+
3. **Add environment variables** from your `.env.example` file
4. **Deploy!** Render will automatically handle the rest

## Configuration

All configuration is managed through environment variables. See `.env.example` for all available settings.

### Required Environment Variables

- `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`: Database connection (see [Database Setup Guide](docs/database-setup.md))
- `GITHUB_TOKEN`: GitHub API access
- `JIRA_URL`, `JIRA_USERNAME`, `JIRA_TOKEN`: JIRA integration  
- `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`: Slack integration
- `SECRET_KEY`: Application security

### Database Setup

DevSync AI uses Supabase as its database. Follow the [Database Setup Guide](docs/database-setup.md) for detailed instructions on:

1. Creating a Supabase project
2. Getting your connection credentials
3. Running database migrations
4. Verifying the setup

Quick verification:
```bash
uv run python scripts/check_database.py
```

## Development

The project follows a modular architecture:

- `devsync_ai/api/`: REST API endpoints
- `devsync_ai/webhooks/`: Webhook handlers for external services
- `devsync_ai/services/`: Business logic and external API integrations
- `devsync_ai/models/`: Data models and validation
- `devsync_ai/scheduler/`: Background tasks and automation
- `devsync_ai/utils/`: Utility functions and helpers

## License

MIT License