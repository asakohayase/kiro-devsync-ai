#!/usr/bin/env python3
"""
Send simple Slack notification for Agent Hook Architecture Steering document update.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any


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


async def send_notification_with_webhook():
    """Send notification using webhook URL if available."""
    import aiohttp
    
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    
    if not webhook_url:
        print("❌ No Slack webhook URL found in environment variables")
        print("💡 Set SLACK_WEBHOOK_URL environment variable to send notifications")
        return
    
    try:
        message_payload = create_steering_update_message()
        
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=message_payload) as response:
                if response.status == 200:
                    print("✅ Steering update notification sent successfully!")
                    print(f"📝 Message: {message_payload['text']}")
                else:
                    print(f"❌ Failed to send notification: HTTP {response.status}")
                    
    except Exception as e:
        print(f"❌ Error sending notification: {str(e)}")


def print_message_preview():
    """Print a preview of the message that would be sent."""
    message = create_steering_update_message()
    
    print("🔍 Slack Message Preview:")
    print("=" * 50)
    print(f"Fallback Text: {message['text']}")
    print("\nBlocks Structure:")
    
    for i, block in enumerate(message['blocks']):
        block_type = block.get('type', 'unknown')
        print(f"  {i+1}. {block_type.upper()}")
        
        if block_type == 'header':
            print(f"     Text: {block['text']['text']}")
        elif block_type == 'section':
            if 'text' in block:
                text = block['text']['text'][:100] + "..." if len(block['text']['text']) > 100 else block['text']['text']
                print(f"     Text: {text}")
            if 'fields' in block:
                print(f"     Fields: {len(block['fields'])} field(s)")
        elif block_type == 'actions':
            print(f"     Buttons: {len(block['elements'])} button(s)")
    
    print("=" * 50)


if __name__ == "__main__":
    print("🚀 Agent Hook Architecture Steering Update Notification")
    print()
    
    # Always show preview
    print_message_preview()
    print()
    
    # Try to send if webhook URL is available
    print("📤 Attempting to send notification...")
    asyncio.run(send_notification_with_webhook())