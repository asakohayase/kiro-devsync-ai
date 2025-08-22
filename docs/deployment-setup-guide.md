# JIRA Slack Agent Hooks - Deployment and Setup Guide

## Overview

This guide provides comprehensive instructions for deploying and setting up the JIRA Slack Agent Hooks system. Follow these steps to get the system running in your environment.

## Prerequisites

### System Requirements

- **Python**: 3.9 or higher
- **Database**: PostgreSQL 12+ or SQLite 3.35+
- **Memory**: Minimum 512MB RAM, recommended 2GB+
- **Storage**: Minimum 1GB free space
- **Network**: HTTPS access to JIRA and Slack APIs

### Required Accounts and Access

- **JIRA Admin Access**: To configure webhooks
- **Slack App Management**: To create and configure Slack bot
- **Database Access**: To create tables and manage data
- **Server Access**: To deploy and run the application

### Dependencies

```bash
# Core dependencies (automatically installed)
fastapi>=0.68.0
uvicorn>=0.15.0
sqlalchemy>=1.4.0
alembic>=1.7.0
pydantic>=1.8.0
httpx>=0.24.0
pyyaml>=5.4.0
python-multipart>=0.0.5
```

## Installation

### 1. Clone and Setup Repository

```bash
# Clone the repository
git clone https://github.com/your-org/devsync-ai.git
cd devsync-ai

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies using uv (recommended)
pip install uv
uv sync

# Or install with pip
pip install -r requirements.txt
```

### 2. Database Setup

#### PostgreSQL Setup (Recommended for Production)

```bash
# Create database
createdb devsync_ai

# Set environment variables
export DATABASE_URL="postgresql://username:password@localhost:5432/devsync_ai"
export DATABASE_TYPE="postgresql"
```

#### SQLite Setup (Development/Testing)

```bash
# SQLite will be created automatically
export DATABASE_URL="sqlite:///./devsync_ai.db"
export DATABASE_TYPE="sqlite"
```

#### Run Database Migrations

```bash
# Run initial migrations
uv run python -m devsync_ai.database.migrations.runner

# Or run specific migration scripts
uv run python scripts/migrate_hook_data_storage.py
```

### 3. Configuration Setup

#### Environment Variables

Create a `.env` file in the project root:

```bash
# .env file
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/devsync_ai
DATABASE_TYPE=postgresql

# JIRA Configuration
JIRA_BASE_URL=https://your-company.atlassian.net
JIRA_USERNAME=your-jira-user@company.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_WEBHOOK_SECRET=your-webhook-secret-key

# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_APP_TOKEN=xapp-your-slack-app-token
SLACK_SIGNING_SECRET=your-slack-signing-secret

# Application Configuration
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=false

# Security
SECRET_KEY=your-secret-key-for-jwt-tokens
WEBHOOK_SECRET=your-webhook-validation-secret

# Analytics and Monitoring
ANALYTICS_ENABLED=true
MONITORING_ENABLED=true
LOG_LEVEL=INFO

# External Integrations (Optional)
PAGERDUTY_API_KEY=your-pagerduty-key
DATADOG_API_KEY=your-datadog-key
```

#### Configuration Files

Copy and customize configuration templates:

```bash
# Copy configuration templates
cp config/jira_webhook_config.example.yaml config/jira_webhook_config.yaml
cp config/notification_config.example.yaml config/notification_config.yaml
cp config/analytics_config.example.yaml config/analytics_config.yaml

# Copy team configuration templates
cp config/team_config_example.yaml config/team_engineering_hooks.yaml
cp config/team_config_example.yaml config/team_qa_hooks.yaml
```

## JIRA Configuration

### 1. Create JIRA Webhook

1. **Access JIRA Admin Panel**
   - Go to JIRA Administration → System → Webhooks
   - Click "Create a WebHook"

2. **Configure Webhook Settings**
   ```
   Name: DevSync AI Hook System
   Status: Enabled
   URL: https://your-domain.com/webhooks/jira
   Description: Webhook for DevSync AI agent hooks
   ```

3. **Select Events**
   - Issue created
   - Issue updated
   - Issue deleted
   - Issue assigned
   - Issue commented

4. **Configure Security**
   - Add webhook secret in "Secret" field
   - Use the same value as `JIRA_WEBHOOK_SECRET` in your `.env` file

5. **Test Webhook**
   ```bash
   # Test webhook endpoint
   curl -X POST https://your-domain.com/webhooks/jira/test \
     -H "Content-Type: application/json" \
     -H "X-Atlassian-Webhook-Identifier: test" \
     -d '{"test": true}'
   ```

### 2. JIRA API Token Setup

1. **Generate API Token**
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Click "Create API token"
   - Copy the token to `JIRA_API_TOKEN` in your `.env` file

2. **Test JIRA Connection**
   ```bash
   # Test JIRA API connection
   uv run python scripts/test_jira_connection.py
   ```

## Slack Configuration

### 1. Create Slack App

1. **Create New App**
   - Go to https://api.slack.com/apps
   - Click "Create New App" → "From scratch"
   - App Name: "DevSync AI"
   - Workspace: Select your workspace

2. **Configure OAuth Scopes**
   - Go to "OAuth & Permissions"
   - Add Bot Token Scopes:
     ```
     chat:write
     chat:write.public
     channels:read
     groups:read
     im:read
     mpim:read
     users:read
     users:read.email
     ```

3. **Install App to Workspace**
   - Click "Install to Workspace"
   - Copy "Bot User OAuth Token" to `SLACK_BOT_TOKEN` in `.env`

4. **Configure Event Subscriptions (Optional)**
   - Go to "Event Subscriptions"
   - Enable Events: On
   - Request URL: `https://your-domain.com/slack/events`

### 2. Slack Channel Setup

1. **Create Required Channels**
   ```bash
   # Create channels in Slack
   /create #dev-updates
   /create #team-assignments
   /create #ticket-discussions
   /create #blockers
   /create #deployments
   ```

2. **Invite Bot to Channels**
   ```bash
   # In each channel, invite the bot
   /invite @devsync-ai
   ```

3. **Test Slack Connection**
   ```bash
   # Test Slack API connection
   uv run python scripts/test_slack_connection.py --channel "#test"
   ```

## Application Deployment

### 1. Development Deployment

```bash
# Start development server
uv run python -m devsync_ai.main

# Or use uvicorn directly
uv run uvicorn devsync_ai.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Production Deployment with Docker

#### Create Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "devsync_ai.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Create Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/devsync_ai
      - JIRA_BASE_URL=${JIRA_BASE_URL}
      - JIRA_API_TOKEN=${JIRA_API_TOKEN}
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
    depends_on:
      - db
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    restart: unless-stopped

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=devsync_ai
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./migrations:/docker-entrypoint-initdb.d
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

volumes:
  postgres_data:
```

#### Deploy with Docker

```bash
# Build and start services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f app

# Run database migrations
docker-compose exec app python -m devsync_ai.database.migrations.runner
```

### 3. Production Deployment with Kubernetes

#### Create Kubernetes Manifests

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: devsync-ai
  labels:
    app: devsync-ai
spec:
  replicas: 3
  selector:
    matchLabels:
      app: devsync-ai
  template:
    metadata:
      labels:
        app: devsync-ai
    spec:
      containers:
      - name: devsync-ai
        image: your-registry/devsync-ai:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: devsync-ai-secrets
              key: database-url
        - name: SLACK_BOT_TOKEN
          valueFrom:
            secretKeyRef:
              name: devsync-ai-secrets
              key: slack-bot-token
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"

---
apiVersion: v1
kind: Service
metadata:
  name: devsync-ai-service
spec:
  selector:
    app: devsync-ai
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: devsync-ai-secrets
type: Opaque
data:
  database-url: <base64-encoded-database-url>
  slack-bot-token: <base64-encoded-slack-token>
  jira-api-token: <base64-encoded-jira-token>
```

#### Deploy to Kubernetes

```bash
# Create secrets
kubectl apply -f k8s/secrets.yaml

# Deploy application
kubectl apply -f k8s/deployment.yaml

# Check deployment status
kubectl get pods -l app=devsync-ai
kubectl get services

# View logs
kubectl logs -l app=devsync-ai -f
```

## Configuration and Testing

### 1. Team Configuration

Edit team configuration files:

```yaml
# config/team_engineering_hooks.yaml
team_id: "engineering"
enabled: true
description: "Engineering team hook configuration"

default_channels:
  status_change: "#eng-updates"
  assignment: "#eng-assignments"
  comment: "#eng-discussions"
  blocker: "#eng-blockers"

hooks:
  status_change:
    enabled: true
    channels: ["#eng-updates"]
    conditions:
      - field: "priority"
        operator: "in"
        values: ["High", "Critical"]
    urgency_mapping:
      "To Do -> In Progress": "low"
      "In Progress -> Done": "medium"
      "In Progress -> Blocked": "high"

  assignment:
    enabled: true
    channels: ["#eng-assignments"]
    workload_warnings: true
    max_tickets_per_assignee: 8

  comment:
    enabled: true
    channels: ["#eng-discussions"]
    conditions:
      - field: "ticket_priority"
        operator: "in"
        values: ["High", "Critical"]

  blocker:
    enabled: true
    channels: ["#eng-blockers"]
    escalation_enabled: true
    escalation_delay_minutes: 15

notification_preferences:
  business_hours_only: false
  timezone: "America/New_York"
  quiet_hours:
    start: "22:00"
    end: "08:00"
  weekend_notifications: false
```

### 2. Validate Configuration

```bash
# Validate all configurations
uv run python scripts/validate_all_configurations.py

# Validate specific team configuration
uv run python scripts/validate_configuration.py --config config/team_engineering_hooks.yaml

# Test configuration loading
uv run python scripts/test_configuration_loading.py --team engineering
```

### 3. Test Hook System

```bash
# Test complete system
uv run python scripts/validate_complete_system.py

# Test specific hook types
uv run python scripts/test_hook_execution.py --hook-type status_change --team engineering

# Simulate webhook events
uv run python scripts/simulate_webhook.py --event-type jira:issue_updated --ticket-key TEST-123
```

## Monitoring and Maintenance

### 1. Health Checks

```bash
# Check system health
curl http://localhost:8000/health

# Check hook system status
curl http://localhost:8000/api/hooks/status

# Check database connectivity
curl http://localhost:8000/health/database
```

### 2. Logging Configuration

```yaml
# config/logging.yaml
version: 1
disable_existing_loggers: false

formatters:
  standard:
    format: '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
  detailed:
    format: '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: standard
    stream: ext://sys.stdout

  file:
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: detailed
    filename: logs/devsync_ai.log
    maxBytes: 10485760  # 10MB
    backupCount: 5

  hook_file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: detailed
    filename: logs/hook_executions.log
    maxBytes: 10485760  # 10MB
    backupCount: 10

loggers:
  devsync_ai:
    level: INFO
    handlers: [console, file]
    propagate: false

  devsync_ai.core.agent_hooks:
    level: DEBUG
    handlers: [hook_file]
    propagate: false

root:
  level: WARNING
  handlers: [console]
```

### 3. Monitoring Setup

```bash
# Start monitoring dashboard
uv run python scripts/start_analytics_dashboard.py

# Start system health monitor
uv run python scripts/start_system_health_monitor.py

# Generate performance report
uv run python scripts/generate_performance_report.py --time-range 24h
```

## Security Considerations

### 1. Webhook Security

```python
# Ensure webhook signature validation is enabled
WEBHOOK_CONFIG = {
    'validate_signature': True,
    'signature_header': 'X-Atlassian-Webhook-Identifier',
    'secret_key': os.environ['JIRA_WEBHOOK_SECRET']
}
```

### 2. API Security

```python
# Configure API authentication
API_CONFIG = {
    'require_authentication': True,
    'jwt_secret': os.environ['SECRET_KEY'],
    'token_expiry_hours': 24
}
```

### 3. Network Security

```bash
# Configure firewall rules
# Allow only necessary ports
ufw allow 8000/tcp  # Application port
ufw allow 443/tcp   # HTTPS
ufw deny 22/tcp     # SSH (if not needed)

# Configure reverse proxy (nginx example)
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   ```bash
   # Check database connectivity
   uv run python scripts/check_database.py
   
   # Reset database
   uv run python scripts/reset_database.py --confirm
   ```

2. **JIRA Webhook Not Working**
   ```bash
   # Test webhook endpoint
   curl -X POST http://localhost:8000/webhooks/jira/test
   
   # Check JIRA webhook configuration
   uv run python scripts/check_jira_webhooks.py
   ```

3. **Slack Notifications Not Sent**
   ```bash
   # Test Slack connection
   uv run python scripts/test_slack_connection.py
   
   # Check bot permissions
   uv run python scripts/check_slack_permissions.py
   ```

### Log Analysis

```bash
# View recent errors
tail -f logs/devsync_ai.log | grep ERROR

# Analyze hook execution patterns
uv run python scripts/analyze_hook_logs.py --time-range 24h

# Generate diagnostic report
uv run python scripts/generate_diagnostic_report.py
```

## Backup and Recovery

### 1. Database Backup

```bash
# PostgreSQL backup
pg_dump devsync_ai > backup_$(date +%Y%m%d_%H%M%S).sql

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups/devsync_ai"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump devsync_ai | gzip > "$BACKUP_DIR/backup_$DATE.sql.gz"
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +7 -delete
```

### 2. Configuration Backup

```bash
# Backup configurations
tar -czf config_backup_$(date +%Y%m%d).tar.gz config/

# Backup to cloud storage (AWS S3 example)
aws s3 cp config_backup_$(date +%Y%m%d).tar.gz s3://your-backup-bucket/devsync-ai/
```

### 3. Recovery Procedures

```bash
# Restore database
gunzip -c backup_20240115_120000.sql.gz | psql devsync_ai

# Restore configurations
tar -xzf config_backup_20240115.tar.gz

# Restart services
docker-compose restart
# or
kubectl rollout restart deployment/devsync-ai
```

## Performance Optimization

### 1. Database Optimization

```sql
-- Add performance indexes
CREATE INDEX CONCURRENTLY idx_hook_executions_team_timestamp 
ON hook_executions(team_id, created_at DESC);

CREATE INDEX CONCURRENTLY idx_hook_executions_success_timestamp 
ON hook_executions(success, created_at DESC);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM hook_executions 
WHERE team_id = 'engineering' 
AND created_at > NOW() - INTERVAL '24 hours';
```

### 2. Application Optimization

```python
# Configure connection pooling
DATABASE_CONFIG = {
    'pool_size': 20,
    'max_overflow': 30,
    'pool_timeout': 30,
    'pool_recycle': 3600
}

# Configure caching
CACHE_CONFIG = {
    'team_configurations': {'ttl': 300, 'max_size': 100},
    'user_data': {'ttl': 600, 'max_size': 1000}
}
```

### 3. Scaling Considerations

```yaml
# Horizontal scaling with load balancer
# docker-compose.scale.yml
version: '3.8'
services:
  app:
    deploy:
      replicas: 3
    environment:
      - WORKER_PROCESSES=2
      - MAX_CONCURRENT_HOOKS=5

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - app
```

This deployment guide provides comprehensive instructions for setting up the JIRA Slack Agent Hooks system in various environments. Follow the steps appropriate for your deployment scenario and refer to the troubleshooting section if you encounter issues.