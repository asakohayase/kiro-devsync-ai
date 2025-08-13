"""
Examples demonstrating the base message template system.
Shows how to create custom templates using the base class.
"""

import json
from datetime import datetime, timedelta
from devsync_ai.core.base_template import (
    SlackMessageTemplate,
    MessageMetadata,
    TeamBranding,
    ChannelConfig,
    UserPreferences,
    AccessibilityOptions,
    MessagePriority,
    EmojiConstants,
    ColorScheme,
    create_team_branding,
    create_channel_config,
    create_user_preferences,
    create_accessibility_options
)


class SimpleNotificationTemplate(SlackMessageTemplate):
    """Simple notification template example."""
    
    def _validate_data(self) -> None:
        """Validate notification data."""
        if not self.data.get('message'):
            raise ValueError("Message is required")
    
    def _build_message_content(self) -> None:
        """Build notification content."""
        message = self.data.get('message')
        priority = self.data.get('priority', 'normal')
        
        # Add priority indicator
        if priority == 'high':
            emoji = EmojiConstants.WARNING
        elif priority == 'urgent':
            emoji = EmojiConstants.ERROR
        else:
            emoji = EmojiConstants.INFO
        
        self.add_section_block(f"{emoji} {message}")
        
        # Add optional details
        details = self.data.get('details')
        if details:
            self.add_section_block(f"*Details:* {details}")
    
    def _get_header_text(self) -> str:
        """Get header text."""
        return "System Notification"
    
    def _get_header_emoji(self) -> str:
        """Get header emoji."""
        priority = self.data.get('priority', 'normal')
        if priority == 'urgent':
            return EmojiConstants.ERROR
        elif priority == 'high':
            return EmojiConstants.WARNING
        return EmojiConstants.INFO


class TaskUpdateTemplate(SlackMessageTemplate):
    """Task update template example."""
    
    def _validate_data(self) -> None:
        """Validate task data."""
        required_fields = ['task_id', 'title', 'status']
        for field in required_fields:
            if not self.data.get(field):
                raise ValueError(f"{field} is required")
    
    def _build_message_content(self) -> None:
        """Build task update content."""
        task_id = self.data.get('task_id')
        title = self.data.get('title')
        status = self.data.get('status')
        assignee = self.data.get('assignee', 'Unassigned')
        progress = self.data.get('progress', 0)
        total = self.data.get('total', 100)
        
        # Task header
        status_emoji = self._get_status_emoji(status)
        self.add_section_block(f"*{status_emoji} Task {task_id}: {title}*")
        
        # Task details
        fields = [
            {"type": "mrkdwn", "text": f"*Status:* {status}"},
            {"type": "mrkdwn", "text": f"*Assignee:* {assignee}"}
        ]
        
        if progress and total:
            progress_bar = self._create_progress_bar(progress, total)
            fields.extend([
                {"type": "mrkdwn", "text": f"*Progress:*"},
                {"type": "mrkdwn", "text": progress_bar}
            ])
        
        self.add_fields_block(fields)
        
        # Add description if available
        description = self.data.get('description')
        if description:
            self.add_section_block(f"*Description:* {description}")
        
        # Add action buttons
        self._add_task_actions()
    
    def _add_task_actions(self) -> None:
        """Add task action buttons."""
        task_id = self.data.get('task_id')
        status = self.data.get('status')
        
        buttons = []
        
        # Status-specific buttons
        if status.lower() == 'todo':
            buttons.append(
                self.create_button("Start Task", f"start_task_{task_id}", 
                                 emoji=EmojiConstants.PENDING, style="primary")
            )
        elif status.lower() == 'in_progress':
            buttons.append(
                self.create_button("Complete Task", f"complete_task_{task_id}",
                                 emoji=EmojiConstants.SUCCESS, style="primary")
            )
        
        # Common buttons
        buttons.extend([
            self.create_button("View Details", f"view_task_{task_id}",
                             emoji=EmojiConstants.REVIEW),
            self.create_button("Add Comment", f"comment_task_{task_id}",
                             emoji=EmojiConstants.COMMENT)
        ])
        
        if buttons:
            self.add_actions_block(buttons)
    
    def _get_status_emoji(self, status: str) -> str:
        """Get emoji for task status."""
        status_emojis = {
            'todo': EmojiConstants.PENDING,
            'in_progress': '⏳',
            'review': EmojiConstants.REVIEW,
            'done': EmojiConstants.SUCCESS,
            'blocked': EmojiConstants.BLOCKED
        }
        return status_emojis.get(status.lower(), EmojiConstants.INFO)
    
    def _get_header_text(self) -> str:
        """Get header text."""
        return "Task Update"
    
    def _get_header_emoji(self) -> str:
        """Get header emoji."""
        return EmojiConstants.TICKET


class MetricsReportTemplate(SlackMessageTemplate):
    """Metrics report template example."""
    
    def _validate_data(self) -> None:
        """Validate metrics data."""
        if not self.data.get('metrics'):
            raise ValueError("Metrics data is required")
    
    def _build_message_content(self) -> None:
        """Build metrics report content."""
        metrics = self.data.get('metrics', {})
        period = self.data.get('period', 'Daily')
        
        # Report header
        self.add_section_block(f"*📊 {period} Metrics Report*")
        
        # Key metrics
        self._add_key_metrics(metrics)
        
        # Trends if available
        trends = self.data.get('trends', {})
        if trends:
            self._add_trends(trends)
        
        # Charts/visualizations
        chart_url = self.data.get('chart_url')
        if chart_url:
            self.add_image_block(chart_url, f"{period} metrics chart", "Metrics Visualization")
        
        # Action buttons
        self._add_metrics_actions()
    
    def _add_key_metrics(self, metrics: dict) -> None:
        """Add key metrics section."""
        if not metrics:
            return
        
        fields = []
        for key, value in metrics.items():
            # Format metric name
            metric_name = key.replace('_', ' ').title()
            
            # Format value with appropriate emoji
            if isinstance(value, (int, float)):
                if 'error' in key.lower() or 'fail' in key.lower():
                    emoji = EmojiConstants.ERROR if value > 0 else EmojiConstants.SUCCESS
                elif 'success' in key.lower() or 'complete' in key.lower():
                    emoji = EmojiConstants.SUCCESS
                else:
                    emoji = "📈"
                
                formatted_value = f"{emoji} {value:,}"
            else:
                formatted_value = str(value)
            
            fields.append({
                "type": "mrkdwn",
                "text": f"*{metric_name}:* {formatted_value}"
            })
        
        if fields:
            self.add_fields_block(fields)
    
    def _add_trends(self, trends: dict) -> None:
        """Add trends section."""
        if not trends:
            return
        
        self.add_divider_block()
        trend_text = "*📈 Trends:*\n"
        
        for metric, change in trends.items():
            metric_name = metric.replace('_', ' ').title()
            
            if isinstance(change, (int, float)):
                if change > 0:
                    trend_emoji = "📈"
                    change_text = f"+{change:.1f}%"
                elif change < 0:
                    trend_emoji = "📉"
                    change_text = f"{change:.1f}%"
                else:
                    trend_emoji = "➡️"
                    change_text = "No change"
            else:
                trend_emoji = "📊"
                change_text = str(change)
            
            trend_text += f"• {trend_emoji} {metric_name}: {change_text}\n"
        
        self.add_section_block(trend_text.strip())
    
    def _add_metrics_actions(self) -> None:
        """Add metrics action buttons."""
        buttons = [
            self.create_button("View Dashboard", "view_dashboard",
                             emoji="📊", style="primary"),
            self.create_button("Download Report", "download_report",
                             emoji="📥"),
            self.create_button("Schedule Report", "schedule_report",
                             emoji="📅")
        ]
        
        self.add_actions_block(buttons)
    
    def _get_header_text(self) -> str:
        """Get header text."""
        period = self.data.get('period', 'Daily')
        return f"{period} Metrics Report"
    
    def _get_header_emoji(self) -> str:
        """Get header emoji."""
        return "📊"


def example_simple_notification():
    """Example simple notification."""
    print("=== Simple Notification Example ===")
    
    data = {
        "message": "System maintenance completed successfully",
        "priority": "normal",
        "details": "All services are now running normally. Downtime was 15 minutes."
    }
    
    # Basic notification
    template = SimpleNotificationTemplate(data)
    message = template.get_message()
    
    print("Basic notification:")
    print(json.dumps(message, indent=2))
    
    # High priority notification
    urgent_data = {
        "message": "Critical security patch applied",
        "priority": "urgent",
        "details": "All users must update their passwords within 24 hours."
    }
    
    urgent_template = SimpleNotificationTemplate(urgent_data)
    urgent_message = urgent_template.get_message()
    
    print("\nUrgent notification:")
    print(f"Blocks: {len(urgent_message['blocks'])}")
    
    return message


def example_task_update():
    """Example task update."""
    print("\n=== Task Update Example ===")
    
    data = {
        "task_id": "TASK-123",
        "title": "Implement user authentication",
        "status": "In Progress",
        "assignee": "Alice Johnson",
        "progress": 65,
        "total": 100,
        "description": "Adding OAuth2 authentication with Google and GitHub providers"
    }
    
    template = TaskUpdateTemplate(data)
    message = template.get_message()
    
    print("Task update:")
    print(json.dumps(message, indent=2))
    
    return message


def example_metrics_report():
    """Example metrics report."""
    print("\n=== Metrics Report Example ===")
    
    data = {
        "period": "Weekly",
        "metrics": {
            "total_deployments": 23,
            "successful_deployments": 21,
            "failed_deployments": 2,
            "average_build_time": 8.5,
            "code_coverage": 87.3,
            "active_users": 1250
        },
        "trends": {
            "deployments": 15.2,
            "build_time": -12.5,
            "code_coverage": 3.1,
            "active_users": 8.7
        },
        "chart_url": "https://example.com/metrics-chart.png"
    }
    
    template = MetricsReportTemplate(data)
    message = template.get_message()
    
    print("Metrics report:")
    print(json.dumps(message, indent=2))
    
    return message


def example_with_team_branding():
    """Example with team branding."""
    print("\n=== Team Branding Example ===")
    
    # Create custom team branding
    branding = create_team_branding(
        "DevOps Team",
        primary_color="#ff6b35",
        footer_text="DevOps Team • Keeping systems running 24/7",
        custom_emojis={
            "success": ":white_check_mark:",
            "warning": ":warning:",
            "error": ":x:"
        },
        date_format="%B %d, %Y at %I:%M %p"
    )
    
    data = {
        "message": "Deployment pipeline updated",
        "priority": "normal",
        "details": "New security scanning step added to all deployment pipelines"
    }
    
    template = SimpleNotificationTemplate(data, team_branding=branding)
    message = template.get_message()
    
    print("Message with team branding:")
    print(f"Blocks: {len(message['blocks'])}")
    
    # Check footer for custom branding
    for block in message['blocks']:
        if block.get('type') == 'context':
            print("Footer elements:", [elem.get('text') for elem in block.get('elements', [])])
    
    return message


def example_with_accessibility():
    """Example with accessibility features."""
    print("\n=== Accessibility Example ===")
    
    # Create accessibility options
    accessibility = create_accessibility_options(
        screen_reader_optimized=True,
        high_contrast=True,
        alt_text_required=True
    )
    
    data = {
        "task_id": "TASK-456",
        "title": "Accessibility improvements",
        "status": "Done",
        "assignee": "Accessibility Team",
        "progress": 100,
        "total": 100,
        "description": "Implemented screen reader support and high contrast mode"
    }
    
    template = TaskUpdateTemplate(data, accessibility_options=accessibility)
    message = template.get_message()
    
    print("Accessible task update:")
    print(f"Blocks: {len(message['blocks'])}")
    
    # Check for accessibility features
    for block in message['blocks']:
        if block.get('type') == 'header':
            text = block.get('text', {}).get('text', '')
            if text.startswith('Heading:'):
                print("✅ Screen reader optimization applied")
    
    return message


def example_with_channel_config():
    """Example with channel configuration."""
    print("\n=== Channel Configuration Example ===")
    
    # Create channel config for compact mode
    channel_config = create_channel_config(
        "C1234567890",
        "dev-notifications",
        compact_mode=True,
        threading_enabled=True,
        max_blocks=10
    )
    
    data = {
        "message": "Build completed",
        "priority": "normal",
        "details": "All tests passed, deployment ready"
    }
    
    template = SimpleNotificationTemplate(data, channel_config=channel_config)
    message = template.get_message()
    
    print("Compact mode message:")
    print(f"Blocks: {len(message['blocks'])}")
    
    # Should have fewer blocks due to compact mode
    header_count = sum(1 for block in message['blocks'] if block.get('type') == 'header')
    context_count = sum(1 for block in message['blocks'] if block.get('type') == 'context')
    
    print(f"Headers: {header_count}, Context blocks: {context_count}")
    print("✅ Compact mode reduces header/footer visibility")
    
    return message


def example_with_user_preferences():
    """Example with user preferences."""
    print("\n=== User Preferences Example ===")
    
    # Create user preferences
    user_prefs = create_user_preferences(
        "U1234567890",
        timezone="America/New_York",
        date_format="%m/%d/%Y %I:%M %p",
        compact_mode=False,
        notification_level="detailed"
    )
    
    data = {
        "metrics": {
            "api_requests": 15420,
            "response_time": 245,
            "error_rate": 0.02
        },
        "period": "Hourly",
        "trends": {
            "api_requests": 12.5,
            "response_time": -8.3,
            "error_rate": -15.7
        }
    }
    
    template = MetricsReportTemplate(data, user_preferences=user_prefs)
    message = template.get_message()
    
    print("Message with user preferences:")
    print(f"Blocks: {len(message['blocks'])}")
    
    return message


def example_error_handling():
    """Example error handling."""
    print("\n=== Error Handling Example ===")
    
    # Try to create template with missing required data
    invalid_data = {
        "description": "This is missing the required title field"
    }
    
    template = TaskUpdateTemplate(invalid_data)
    
    print(f"Has errors: {template.has_errors()}")
    print(f"Errors: {template.get_errors()}")
    
    # Should still create a message (error message)
    message = template.get_message()
    print(f"Error message blocks: {len(message['blocks'])}")
    
    # Check analytics for error tracking
    analytics = template.get_analytics_data()
    print(f"Has errors in analytics: {analytics['has_errors']}")
    
    return message


def example_analytics_tracking():
    """Example analytics tracking."""
    print("\n=== Analytics Tracking Example ===")
    
    data = {
        "message": "Feature deployment completed",
        "priority": "high",
        "details": "New user dashboard is now live"
    }
    
    # Create template with metadata
    metadata = MessageMetadata(
        template_name="deployment_notification",
        template_version="2.1",
        user_id="U1234567890",
        channel_id="C0987654321",
        priority=MessagePriority.HIGH,
        tags=["deployment", "feature", "dashboard"]
    )
    
    template = SimpleNotificationTemplate(data, metadata=metadata)
    
    # Add custom analytics data
    template.add_analytics_data("deployment_id", "deploy-456")
    template.add_analytics_data("feature_name", "user_dashboard")
    template.add_analytics_data("environment", "production")
    
    analytics = template.get_analytics_data()
    
    print("Analytics data:")
    print(json.dumps(analytics, indent=2, default=str))
    
    return analytics


if __name__ == "__main__":
    print("DevSync AI Base Template Examples")
    print("=" * 50)
    
    # Run all examples
    example_simple_notification()
    example_task_update()
    example_metrics_report()
    example_with_team_branding()
    example_with_accessibility()
    example_with_channel_config()
    example_with_user_preferences()
    example_error_handling()
    example_analytics_tracking()
    
    print("\n" + "=" * 50)
    print("All base template examples completed successfully!")
    print("The base template system provides:")
    print("✅ Consistent formatting and branding")
    print("✅ Accessibility features")
    print("✅ Error handling and validation")
    print("✅ Analytics and tracking")
    print("✅ Flexible configuration options")
    print("✅ Mobile-optimized responsive design")