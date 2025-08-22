# Team Configuration Examples and Templates

## Overview

This document provides comprehensive examples and templates for configuring JIRA Slack Agent Hooks for different team types and workflows. Each example includes detailed explanations and customization options.

## Basic Team Configuration Template

### Default Configuration
```yaml
# config/team_default_hooks.yaml
team_id: "default"
enabled: true
default_channels:
  status_change: "#dev-updates"
  assignment: "#team-assignments"
  comment: "#ticket-discussions"
  blocker: "#blockers"

hooks:
  status_change:
    enabled: true
    channels: ["#dev-updates"]
    conditions:
      - field: "priority"
        operator: "in"
        values: ["High", "Critical"]
    urgency_mapping:
      "To Do -> In Progress": "low"
      "In Progress -> Done": "medium"
      "In Progress -> Blocked": "high"
      "Blocked -> In Progress": "medium"
    
  assignment:
    enabled: true
    channels: ["#team-assignments"]
    workload_warnings: true
    max_tickets_per_assignee: 5
    
  comment:
    enabled: true
    channels: ["#ticket-discussions"]
    conditions:
      - field: "ticket_priority"
        operator: "in"
        values: ["High", "Critical"]
    
  blocker:
    enabled: true
    channels: ["#blockers"]
    escalation_enabled: true
    escalation_delay_minutes: 30

notification_preferences:
  business_hours_only: false
  timezone: "UTC"
  quiet_hours:
    start: "22:00"
    end: "08:00"
  weekend_notifications: true
```

## Engineering Team Configuration

### Full-Stack Development Team
```yaml
# config/team_engineering_hooks.yaml
team_id: "engineering"
enabled: true
description: "Full-stack development team with frontend and backend focus"

default_channels:
  status_change: "#eng-updates"
  assignment: "#eng-assignments"
  comment: "#eng-discussions"
  blocker: "#eng-blockers"
  deployment: "#eng-deployments"

hooks:
  status_change:
    enabled: true
    channels: ["#eng-updates"]
    conditions:
      - field: "project"
        operator: "in"
        values: ["WEBAPP", "API", "MOBILE"]
      - field: "priority"
        operator: "in"
        values: ["Medium", "High", "Critical"]
    urgency_mapping:
      "To Do -> In Progress": "low"
      "In Progress -> Code Review": "medium"
      "Code Review -> Testing": "medium"
      "Testing -> Done": "low"
      "In Progress -> Blocked": "high"
      "Any -> Critical": "critical"
    custom_templates:
      status_change: "engineering_status_template"
    
  assignment:
    enabled: true
    channels: ["#eng-assignments"]
    workload_warnings: true
    max_tickets_per_assignee: 8
    conditions:
      - field: "component"
        operator: "in"
        values: ["Frontend", "Backend", "API", "Database"]
    workload_analysis:
      enabled: true
      skill_based_warnings: true
      capacity_thresholds:
        junior: 5
        mid: 8
        senior: 10
        lead: 12
    
  comment:
    enabled: true
    channels: ["#eng-discussions"]
    conditions:
      - field: "ticket_priority"
        operator: "in"
        values: ["High", "Critical"]
      - field: "status"
        operator: "in"
        values: ["In Progress", "Code Review", "Testing"]
    keyword_filters:
      high_priority: ["blocker", "urgent", "production", "critical"]
      technical: ["bug", "error", "exception", "performance"]
    
  blocker:
    enabled: true
    channels: ["#eng-blockers", "#eng-alerts"]
    escalation_enabled: true
    escalation_delay_minutes: 15
    escalation_channels: ["#eng-leads", "#product-team"]
    conditions:
      - field: "labels"
        operator: "contains"
        value: "blocked"
    auto_escalation_rules:
      - condition: "blocker_duration > 2 hours"
        action: "notify_leads"
      - condition: "blocker_duration > 4 hours"
        action: "notify_product"

custom_rules:
  deployment_notifications:
    enabled: true
    channels: ["#eng-deployments"]
    conditions:
      - field: "status"
        operator: "equals"
        value: "Ready for Deployment"
    
  code_review_reminders:
    enabled: true
    channels: ["#eng-code-reviews"]
    conditions:
      - field: "status"
        operator: "equals"
        value: "Code Review"
    reminder_schedule:
      initial_delay_hours: 4
      reminder_interval_hours: 8
      max_reminders: 3

notification_preferences:
  business_hours_only: false
  timezone: "America/New_York"
  quiet_hours:
    start: "23:00"
    end: "07:00"
  weekend_notifications: false
  urgent_override: true
```

## QA Team Configuration

### Quality Assurance Team
```yaml
# config/team_qa_hooks.yaml
team_id: "qa"
enabled: true
description: "Quality assurance team focused on testing and bug tracking"

default_channels:
  status_change: "#qa-updates"
  assignment: "#qa-assignments"
  comment: "#qa-discussions"
  blocker: "#qa-blockers"
  bug_reports: "#qa-bugs"

hooks:
  status_change:
    enabled: true
    channels: ["#qa-updates"]
    conditions:
      - field: "issue_type"
        operator: "in"
        values: ["Bug", "Test", "Story"]
      - field: "status"
        operator: "in"
        values: ["Ready for Testing", "In Testing", "Testing Complete", "Failed Testing"]
    urgency_mapping:
      "Ready for Testing -> In Testing": "medium"
      "In Testing -> Testing Complete": "low"
      "In Testing -> Failed Testing": "high"
      "Failed Testing -> In Progress": "medium"
    
  assignment:
    enabled: true
    channels: ["#qa-assignments"]
    workload_warnings: true
    max_tickets_per_assignee: 6
    conditions:
      - field: "issue_type"
        operator: "in"
        values: ["Bug", "Test", "Story"]
    specialization_routing:
      automation: ["automation_tester_1", "automation_tester_2"]
      manual: ["manual_tester_1", "manual_tester_2", "manual_tester_3"]
      performance: ["performance_tester_1"]
    
  comment:
    enabled: true
    channels: ["#qa-discussions"]
    conditions:
      - field: "issue_type"
        operator: "equals"
        value: "Bug"
      - field: "priority"
        operator: "in"
        values: ["High", "Critical"]
    keyword_filters:
      test_related: ["test case", "test plan", "automation", "regression"]
      bug_related: ["reproduce", "steps", "environment", "browser"]
    
  blocker:
    enabled: true
    channels: ["#qa-blockers"]
    escalation_enabled: true
    escalation_delay_minutes: 20
    conditions:
      - field: "labels"
        operator: "contains_any"
        values: ["test-blocked", "environment-issue", "data-issue"]

custom_rules:
  bug_severity_alerts:
    enabled: true
    channels: ["#qa-bugs", "#eng-alerts"]
    conditions:
      - field: "issue_type"
        operator: "equals"
        value: "Bug"
      - field: "priority"
        operator: "equals"
        value: "Critical"
    immediate_notification: true
    
  test_completion_summary:
    enabled: true
    channels: ["#qa-reports"]
    trigger: "daily_summary"
    schedule: "18:00"
    include_metrics: true

notification_preferences:
  business_hours_only: true
  timezone: "America/Los_Angeles"
  quiet_hours:
    start: "18:00"
    end: "09:00"
  weekend_notifications: false
  critical_override: true
```

## Product Team Configuration

### Product Management Team
```yaml
# config/team_product_hooks.yaml
team_id: "product"
enabled: true
description: "Product management team focused on feature delivery and stakeholder communication"

default_channels:
  status_change: "#product-updates"
  assignment: "#product-assignments"
  comment: "#product-discussions"
  blocker: "#product-blockers"
  milestone: "#product-milestones"

hooks:
  status_change:
    enabled: true
    channels: ["#product-updates"]
    conditions:
      - field: "issue_type"
        operator: "in"
        values: ["Epic", "Story", "Feature"]
      - field: "priority"
        operator: "in"
        values: ["Medium", "High", "Critical"]
    urgency_mapping:
      "Backlog -> In Progress": "medium"
      "In Progress -> Done": "low"
      "Any -> Blocked": "high"
    stakeholder_notifications:
      enabled: true
      epic_updates: ["#stakeholder-updates"]
      milestone_updates: ["#executive-updates"]
    
  assignment:
    enabled: false  # Product team doesn't need assignment notifications
    
  comment:
    enabled: true
    channels: ["#product-discussions"]
    conditions:
      - field: "issue_type"
        operator: "in"
        values: ["Epic", "Story"]
      - field: "comment_author_role"
        operator: "in"
        values: ["stakeholder", "customer", "executive"]
    vip_commenters:
      - "ceo@company.com"
      - "cto@company.com"
      - "product.director@company.com"
    
  blocker:
    enabled: true
    channels: ["#product-blockers", "#executive-alerts"]
    escalation_enabled: true
    escalation_delay_minutes: 10
    conditions:
      - field: "issue_type"
        operator: "in"
        values: ["Epic", "Story", "Feature"]
    immediate_escalation:
      - field: "labels"
        operator: "contains"
        value: "customer-impact"

custom_rules:
  milestone_tracking:
    enabled: true
    channels: ["#product-milestones"]
    conditions:
      - field: "fix_version"
        operator: "not_empty"
    milestone_alerts:
      at_risk: 7  # days before due date
      overdue: 0  # immediate notification
    
  customer_feedback:
    enabled: true
    channels: ["#customer-feedback"]
    conditions:
      - field: "labels"
        operator: "contains_any"
        values: ["customer-request", "user-feedback", "support-ticket"]
    priority_routing:
      high_value_customers: ["#vip-customers"]
      enterprise_customers: ["#enterprise-support"]

notification_preferences:
  business_hours_only: true
  timezone: "America/New_York"
  quiet_hours:
    start: "19:00"
    end: "08:00"
  weekend_notifications: false
  executive_override: true
```

## DevOps Team Configuration

### Infrastructure and Operations Team
```yaml
# config/team_devops_hooks.yaml
team_id: "devops"
enabled: true
description: "DevOps team managing infrastructure, deployments, and operations"

default_channels:
  status_change: "#devops-updates"
  assignment: "#devops-assignments"
  comment: "#devops-discussions"
  blocker: "#devops-incidents"
  deployment: "#deployments"
  infrastructure: "#infrastructure"

hooks:
  status_change:
    enabled: true
    channels: ["#devops-updates"]
    conditions:
      - field: "component"
        operator: "in"
        values: ["Infrastructure", "Deployment", "Monitoring", "Security"]
      - field: "labels"
        operator: "contains_any"
        values: ["ops", "infrastructure", "deployment", "security"]
    urgency_mapping:
      "To Do -> In Progress": "low"
      "In Progress -> Done": "low"
      "Any -> Blocked": "critical"  # Infrastructure blockers are critical
    
  assignment:
    enabled: true
    channels: ["#devops-assignments"]
    workload_warnings: true
    max_tickets_per_assignee: 4  # DevOps work is typically more complex
    conditions:
      - field: "component"
        operator: "in"
        values: ["Infrastructure", "Deployment", "Monitoring"]
    on_call_routing:
      enabled: true
      schedule_integration: "pagerduty"
    
  comment:
    enabled: true
    channels: ["#devops-discussions"]
    conditions:
      - field: "priority"
        operator: "in"
        values: ["High", "Critical"]
      - field: "labels"
        operator: "contains_any"
        values: ["incident", "outage", "security"]
    keyword_filters:
      incident_keywords: ["down", "outage", "error", "failed", "timeout"]
      security_keywords: ["breach", "vulnerability", "unauthorized", "attack"]
    
  blocker:
    enabled: true
    channels: ["#devops-incidents", "#on-call-alerts"]
    escalation_enabled: true
    escalation_delay_minutes: 5  # Fast escalation for infrastructure issues
    conditions:
      - field: "labels"
        operator: "contains_any"
        values: ["incident", "outage", "critical-infrastructure"]
    pager_integration:
      enabled: true
      severity_mapping:
        critical: "P1"
        high: "P2"
        medium: "P3"

custom_rules:
  deployment_notifications:
    enabled: true
    channels: ["#deployments"]
    conditions:
      - field: "labels"
        operator: "contains"
        value: "deployment"
    deployment_stages:
      - stage: "staging"
        channel: "#staging-deployments"
      - stage: "production"
        channel: "#production-deployments"
        require_approval: true
    
  infrastructure_monitoring:
    enabled: true
    channels: ["#infrastructure"]
    conditions:
      - field: "component"
        operator: "equals"
        value: "Infrastructure"
    monitoring_integration:
      datadog: true
      newrelic: true
      prometheus: true
    
  security_alerts:
    enabled: true
    channels: ["#security-alerts", "#devops-incidents"]
    conditions:
      - field: "labels"
        operator: "contains_any"
        values: ["security", "vulnerability", "cve"]
    immediate_notification: true
    security_team_notification: true

notification_preferences:
  business_hours_only: false  # DevOps operates 24/7
  timezone: "UTC"
  weekend_notifications: true
  on_call_override: true
  incident_escalation: true
```

## Small Team Configuration

### Startup/Small Team Configuration
```yaml
# config/team_small_hooks.yaml
team_id: "small-team"
enabled: true
description: "Small team configuration with simplified workflows"

default_channels:
  all_updates: "#team-updates"
  blockers: "#blockers"

hooks:
  status_change:
    enabled: true
    channels: ["#team-updates"]
    conditions:
      - field: "priority"
        operator: "in"
        values: ["High", "Critical"]
    simple_notifications: true
    
  assignment:
    enabled: true
    channels: ["#team-updates"]
    workload_warnings: false  # Small team, everyone knows workload
    
  comment:
    enabled: true
    channels: ["#team-updates"]
    conditions:
      - field: "priority"
        operator: "equals"
        value: "Critical"
    
  blocker:
    enabled: true
    channels: ["#blockers", "#team-updates"]
    escalation_enabled: false  # Direct communication in small teams

notification_preferences:
  business_hours_only: false
  timezone: "America/New_York"
  consolidated_notifications: true  # Combine multiple notifications
  simple_formatting: true
```

## Advanced Configuration Options

### Conditional Logic Examples

#### Complex Condition Matching
```yaml
hooks:
  status_change:
    conditions:
      # AND logic (all conditions must match)
      - field: "priority"
        operator: "equals"
        value: "High"
      - field: "assignee"
        operator: "in"
        values: ["john.doe", "jane.smith"]
      
      # OR logic using multiple condition sets
      or_conditions:
        - conditions:
            - field: "labels"
              operator: "contains"
              value: "urgent"
        - conditions:
            - field: "status"
              operator: "equals"
              value: "Blocked"
      
      # NOT logic
      not_conditions:
        - field: "issue_type"
          operator: "equals"
          value: "Sub-task"
```

#### Time-Based Conditions
```yaml
hooks:
  assignment:
    time_conditions:
      business_hours_only: true
      timezone: "America/New_York"
      business_hours:
        monday: ["09:00", "17:00"]
        tuesday: ["09:00", "17:00"]
        wednesday: ["09:00", "17:00"]
        thursday: ["09:00", "17:00"]
        friday: ["09:00", "17:00"]
      holidays:
        - "2024-01-01"  # New Year's Day
        - "2024-07-04"  # Independence Day
        - "2024-12-25"  # Christmas
```

### Custom Template Integration
```yaml
hooks:
  status_change:
    custom_templates:
      template_name: "custom_status_template"
      template_path: "templates/custom/status_change.json"
      fallback_template: "default_status_template"
    template_variables:
      company_name: "Acme Corp"
      support_channel: "#help"
      escalation_contact: "@devops-lead"
```

### Integration with External Systems
```yaml
integrations:
  pagerduty:
    enabled: true
    api_key: "${PAGERDUTY_API_KEY}"
    service_id: "${PAGERDUTY_SERVICE_ID}"
    escalation_policy: "DevOps Escalation"
  
  datadog:
    enabled: true
    api_key: "${DATADOG_API_KEY}"
    tags: ["team:devops", "service:jira-hooks"]
  
  jira_automation:
    enabled: true
    auto_transition: true
    transition_rules:
      - from_status: "In Progress"
        to_status: "Code Review"
        condition: "pull_request_created"
```

## Configuration Validation

### Validation Rules
```yaml
validation:
  required_fields:
    - team_id
    - enabled
    - default_channels
  
  channel_validation:
    format: "^#[a-z0-9-_]+$"
    max_length: 21
    required_permissions: ["chat:write", "chat:write.public"]
  
  condition_validation:
    allowed_operators: ["equals", "in", "contains", "not_equals", "not_in"]
    allowed_fields: ["priority", "status", "assignee", "labels", "component"]
  
  rate_limits:
    max_hooks_per_team: 10
    max_conditions_per_hook: 20
    max_channels_per_hook: 5
```

### Testing Configuration
```yaml
testing:
  dry_run_mode: true
  test_channels: ["#test-notifications"]
  mock_events: true
  validation_only: false
```

## Migration and Deployment

### Configuration Migration
```bash
# Migrate from old configuration format
python scripts/migrate_hook_configurations.py \
  --source config/legacy_hooks.yaml \
  --target config/team_engineering_hooks.yaml \
  --team-id engineering

# Validate configuration
python scripts/validate_hook_configuration.py \
  --config config/team_engineering_hooks.yaml \
  --strict
```

### Deployment Checklist
- [ ] Configuration files validated
- [ ] Slack channels exist and bot has access
- [ ] JIRA webhook configured and tested
- [ ] Team members notified of new notifications
- [ ] Monitoring and alerting configured
- [ ] Rollback plan prepared