#!/usr/bin/env python3
"""
Send development activity notification to Slack.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Any


def create_dev_activity_message(developer: str, changes: Dict[str, Any]) -> Dict[str, Any]:
    """Create a development activity notification message."""
    
    # Count changes by type
    modified_files = changes.get('modified', [])
    new_files = changes.get('new', [])
    deleted_files = changes.get('deleted', [])
    
    total_changes = len(modified_files) + len(new_files) + len(deleted_files)
    
    # Determine activity level
    if total_changes > 50:
        activity_emoji = "🔥"
        activity_level = "High Activity"
    elif total_changes > 20:
        activity_emoji = "⚡"
        activity_level = "Active Development"
    else:
        activity_emoji = "📝"
        activity_level = "Development Update"
    
    # Build blocks
    blocks = []
    
    # Header
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"{activity_emoji} {activity_level} - {developer}",
            "emoji": True
        }
    })
    
    # Summary section
    summary_text = f"*📊 Change Summary:*\n"
    summary_text += f"• {len(new_files)} new files\n"
    summary_text += f"• {len(modified_files)} modified files\n"
    summary_text += f"• {len(deleted_files)} deleted files\n"
    summary_text += f"• {total_changes} total changes"
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": summary_text
        }
    })
    
    # Key changes section
    key_changes = []
    
    # Analyze file types and patterns
    if any('hook' in f.lower() for f in new_files + modified_files):
        key_changes.append("🎣 Agent hooks system development")
    
    if any('analytics' in f.lower() for f in new_files + modified_files):
        key_changes.append("📈 Analytics system implementation")
    
    if any('template' in f.lower() for f in new_files + modified_files):
        key_changes.append("📋 Message template enhancements")
    
    if any('notification' in f.lower() for f in new_files + modified_files):
        key_changes.append("🔔 Notification system updates")
    
    if any('test' in f.lower() for f in new_files + modified_files):
        key_changes.append("🧪 Test coverage improvements")
    
    if any('doc' in f.lower() for f in new_files + modified_files):
        key_changes.append("📚 Documentation updates")
    
    if key_changes:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*🎯 Key Areas:*\n" + "\n".join([f"• {change}" for change in key_changes])
            }
        })
    
    # Recent files (show top 10)
    if new_files or modified_files:
        blocks.append({"type": "divider"})
        
        recent_files = []
        
        # Show new files first
        for file in new_files[:5]:
            recent_files.append(f"🆕 `{file}`")
        
        # Then modified files
        for file in modified_files[:5]:
            recent_files.append(f"📝 `{file}`")
        
        if len(new_files + modified_files) > 10:
            recent_files.append(f"... and {len(new_files + modified_files) - 10} more files")
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📁 Recent Changes:*\n" + "\n".join(recent_files)
            }
        })
    
    # Timestamp
    timestamp = datetime.now().strftime('%I:%M %p on %B %d, %Y')
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"⏰ {timestamp} | 🤖 DevSync AI Activity Monitor"
            }
        ]
    })
    
    # Fallback text
    fallback_text = f"{developer} made {total_changes} changes to the codebase"
    
    return {
        "blocks": blocks,
        "text": fallback_text
    }


async def send_activity_notification():
    """Send the development activity notification."""
    
    # Analyze the git changes
    changes = {
        'modified': [
            '.kiro/specs/jira-slack-agent-hooks/tasks.md',
            'devsync_ai/api/routes.py',
            'devsync_ai/core/exceptions.py',
            'devsync_ai/database/migrations/run_migrations.sql',
            'devsync_ai/webhooks/jira_webhook_handler.py',
            'pyproject.toml',
            'uv.lock'
        ],
        'new': [
            '.kiro/hooks/dev-activity-monitor.kiro.hook',
            'config/analytics_config.example.yaml',
            'config/team_custom_hooks.yaml',
            'config/team_engineering_hooks.yaml',
            'config/team_qa_hooks.yaml',
            'devsync_ai/analytics/analytics_data_manager.py',
            'devsync_ai/analytics/business_metrics_engine.py',
            'devsync_ai/analytics/dashboard_api.py',
            'devsync_ai/analytics/hook_analytics_engine.py',
            'devsync_ai/analytics/hook_monitoring_dashboard.py',
            'devsync_ai/analytics/hook_optimization_engine.py',
            'devsync_ai/analytics/intelligence_engine.py',
            'devsync_ai/analytics/monitoring_data_manager.py',
            'devsync_ai/analytics/productivity_analytics_engine.py',
            'devsync_ai/analytics/real_time_monitoring.py',
            'devsync_ai/analytics/workload_analytics_engine.py',
            'devsync_ai/api/hook_configuration_routes.py',
            'devsync_ai/api/hook_management_routes.py',
            'devsync_ai/core/event_classification_engine.py',
            'devsync_ai/core/hook_configuration_manager.py',
            'devsync_ai/core/hook_configuration_validator.py',
            'devsync_ai/core/hook_error_handler.py',
            'devsync_ai/core/hook_event_processor.py',
            'devsync_ai/core/hook_notification_integration.py',
            'devsync_ai/core/hook_rule_engine.py',
            'devsync_ai/core/hook_template_fallback.py',
            'devsync_ai/core/hook_template_integration.py',
            'devsync_ai/database/hook_data_manager.py',
            'devsync_ai/formatters/hook_message_formatter.py',
            'devsync_ai/hooks/hook_registry_manager.py',
            'devsync_ai/hooks/jira_agent_hooks.py',
            'devsync_ai/templates/hook_templates.py',
            'docs/analytics-system.md',
            'docs/hook-configuration-manager-implementation.md',
            'docs/hook-data-storage.md',
            'docs/hook-event-processor-implementation.md',
            'docs/hook-management-api.md',
            'docs/hook-notification-integration-implementation.md',
            'docs/workload-analysis-implementation.md',
            'examples/hook_error_handler_usage.py',
            'examples/hook_event_processor_usage.py',
            'examples/hook_rule_engine_usage.py',
            'examples/hook_template_integration_examples.py',
            'examples/jira_agent_hooks_integration.py',
            'migrations/create_hook_monitoring_tables.sql',
            'migrations/create_team_hook_configurations.sql',
            'scripts/migrate_hook_data_storage.py',
            'scripts/start_analytics_dashboard.py',
            'scripts/test_hook_data_storage.py',
            'scripts/validate_hook_data_storage.py',
            'scripts/validate_hook_error_handler.py',
            'tests/framework/hook_test_suite.py',
            'tests/framework/integration_test_framework.py',
            'tests/test_agent_hook_integration_flow.py',
            'tests/test_analytics_system.py',
            'tests/test_assignment_hook_workload_analysis.py',
            'tests/test_event_classification_engine.py',
            'tests/test_hook_analytics_engine.py',
            'tests/test_hook_analytics_engine_simple.py',
            'tests/test_hook_analytics_integration.py',
            'tests/test_hook_configuration_manager.py',
            'tests/test_hook_data_storage.py',
            'tests/test_hook_error_handler.py',
            'tests/test_hook_error_handler_advanced.py',
            'tests/test_hook_event_processor.py',
            'tests/test_hook_management_api.py',
            'tests/test_hook_management_api_simple.py',
            'tests/test_hook_notification_integration.py',
            'tests/test_hook_notification_integration_simple.py',
            'tests/test_hook_rule_engine.py',
            'tests/test_hook_template_integration.py',
            'tests/test_jira_agent_hooks.py',
            'tests/test_workload_analytics_engine.py',
            'tests/test_workload_analytics_simple.py',
            'tests/test_workload_integration_simple.py'
        ],
        'deleted': [
            '.kiro/specs/Day2_Progress.md'
        ]
    }
    
    # Create the message
    message = create_dev_activity_message("shubhammohole", changes)
    
    # Check if Slack token is available
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    
    if not slack_token:
        print("❌ Slack bot token not configured - cannot send notification")
        print("📋 Message that would have been sent:")
        print(json.dumps(message, indent=2))
        return
    
    # For now, just display the message since we don't have Slack configured
    print("🚀 Development Activity Notification Generated!")
    print("=" * 60)
    print("📋 Slack Message Content:")
    print(json.dumps(message, indent=2))
    print("=" * 60)
    print("✅ Notification ready to send to team Slack channel")


if __name__ == "__main__":
    asyncio.run(send_activity_notification())