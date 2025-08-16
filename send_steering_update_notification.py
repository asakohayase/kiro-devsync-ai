#!/usr/bin/env python3
"""
Send Slack notification for Agent Hook Architecture Steering document update.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any

from devsync_ai.services.slack import SlackService


def create_steering_update_message() -> Dict[str, Any]:
    """Create a Slack message for the steering document update."""
    
    # Get current timestamp
    timestamp = datetime.now().strftime('%I:%M %p')
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    # Create the message blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📋 Agent Hook Architecture Steering Updated",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*File Modified:* `.kiro/steering/Agent Hook Architecture Steering.md`\n*Developer:* System Update\n*Timestamp:* " + f"{date_str} at {timestamp}"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*🔄 Key Changes Made:*\n• Added YAML front-matter with `inclusion: always`\n• Restructured document with clearer architecture principles\n• Enhanced implementation standards and patterns\n• Added comprehensive testing and security guidelines\n• Expanded extension patterns and plugin architecture"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "*📊 Impact:*\nHigh - Core architecture guidance"
                },
                {
                    "type": "mrkdwn",
                    "text": "*🎯 Category:*\nDocumentation & Standards"
                },
                {
                    "type": "mrkdwn",
                    "text": "*👥 Affects:*\nAll hook developers"
                },
                {
                    "type": "mrkdwn",
                    "text": "*🔧 Action Required:*\nReview new patterns"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📝 Summary:*\nThe Agent Hook Architecture Steering document has been significantly enhanced with comprehensive development patterns, implementation standards, and architectural guidelines. This update provides clearer guidance for hook development, testing, and integration within the DevSync AI project."
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📖 View Document",
                        "emoji": True
                    },
                    "value": "view_steering_doc",
                    "action_id": "view_steering_doc",
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🔍 View Changes",
                        "emoji": True
                    },
                    "value": "view_diff",
                    "action_id": "view_diff"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "💬 Discuss",
                        "emoji": True
                    },
                    "value": "discuss_changes",
                    "action_id": "discuss_changes"
                }
            ]
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"🤖 DevSync AI • {timestamp} • Steering Document Update"
                }
            ]
        }
    ]
    
    # Fallback text for notifications
    fallback_text = "Agent Hook Architecture Steering document has been updated with enhanced development patterns and implementation standards."
    
    return {
        "blocks": blocks,
        "text": fallback_text
    }


async def send_notification():
    """Send the steering update notification to Slack."""
    try:
        # Initialize Slack service
        slack_service = SlackService()
        
        if not slack_service.client:
            print("❌ Slack client not available - notification not sent")
            return
        
        # Create the message
        message_payload = create_steering_update_message()
        
        # Get target channel from environment or use default
        channel = os.getenv("SLACK_CHANNEL", "general")
        
        # Send the message
        result = await slack_service.send_message(
            channel=channel,
            text=message_payload["text"],
            blocks=message_payload["blocks"]
        )
        
        if result.get("ok"):
            print(f"✅ Steering update notification sent to #{channel}")
            print(f"📝 Message: {message_payload['text']}")
        else:
            print(f"❌ Failed to send notification: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error sending notification: {str(e)}")


if __name__ == "__main__":
    print("🚀 Sending Agent Hook Architecture Steering update notification...")
    asyncio.run(send_notification())