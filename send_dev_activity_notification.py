#!/usr/bin/env python3
"""
Development Activity Notification Script
Analyzes recent git changes and sends a formatted Slack notification to the team.
"""

import asyncio
import json
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import os
import aiohttp
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleSlackClient:
    """Simple Slack client for sending messages."""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://slack.com/api"
    
    async def send_message(self, channel: str, blocks: List[Dict], text: str) -> Dict[str, Any]:
        """Send a message to Slack."""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "channel": channel,
            "blocks": blocks,
            "text": text
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat.postMessage",
                headers=headers,
                json=payload
            ) as response:
                return await response.json()


class DevActivityAnalyzer:
    """Analyzes development activity and generates notifications."""
    
    def __init__(self):
        self.slack_token = os.getenv('SLACK_BOT_TOKEN')
        self.slack_client = SimpleSlackClient(self.slack_token) if self.slack_token else None
    
    def get_git_info(self) -> Dict[str, Any]:
        """Get recent git commit information."""
        try:
            # Get the latest commit info
            result = subprocess.run([
                'git', 'show', '--name-only', '--pretty=format:%an|%ae|%ad|%s', 
                '--date=iso', 'HEAD'
            ], capture_output=True, text=True, check=True)
            
            lines = result.stdout.strip().split('\n')
            if not lines:
                return {}
            
            # Parse commit info
            commit_info = lines[0].split('|')
            if len(commit_info) < 4:
                return {}
            
            author_name = commit_info[0]
            author_email = commit_info[1]
            commit_date = commit_info[2]
            commit_message = commit_info[3]
            
            # Get changed files (skip the first line which is commit info)
            changed_files = [line.strip() for line in lines[1:] if line.strip()]
            
            return {
                'author_name': author_name,
                'author_email': author_email,
                'commit_date': commit_date,
                'commit_message': commit_message,
                'changed_files': changed_files
            }
            
        except subprocess.CalledProcessError as e:
            print(f"Error getting git info: {e}")
            return {}
    
    def get_git_status(self) -> Dict[str, List[str]]:
        """Get current git status (modified, added, deleted files)."""
        try:
            result = subprocess.run([
                'git', 'status', '--porcelain'
            ], capture_output=True, text=True, check=True)
            
            modified_files = []
            added_files = []
            deleted_files = []
            
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                
                status = line[:2]
                filename = line[3:].strip()
                
                if status.startswith('M'):
                    modified_files.append(filename)
                elif status.startswith('A') or status.startswith('??'):
                    added_files.append(filename)
                elif status.startswith('D'):
                    deleted_files.append(filename)
            
            return {
                'modified': modified_files,
                'added': added_files,
                'deleted': deleted_files
            }
            
        except subprocess.CalledProcessError as e:
            print(f"Error getting git status: {e}")
            return {'modified': [], 'added': [], 'deleted': []}
    
    def categorize_changes(self, files: List[str]) -> Dict[str, List[str]]:
        """Categorize changed files by type."""
        categories = {
            'core': [],
            'templates': [],
            'tests': [],
            'docs': [],
            'config': [],
            'scripts': [],
            'examples': [],
            'hooks': [],
            'analytics': [],
            'api': [],
            'other': []
        }
        
        for file in files:
            file_lower = file.lower()
            
            if 'devsync_ai/core/' in file:
                categories['core'].append(file)
            elif 'devsync_ai/templates/' in file:
                categories['templates'].append(file)
            elif 'devsync_ai/analytics/' in file:
                categories['analytics'].append(file)
            elif 'devsync_ai/api/' in file:
                categories['api'].append(file)
            elif 'tests/' in file:
                categories['tests'].append(file)
            elif 'docs/' in file:
                categories['docs'].append(file)
            elif 'config/' in file:
                categories['config'].append(file)
            elif 'scripts/' in file:
                categories['scripts'].append(file)
            elif 'examples/' in file:
                categories['examples'].append(file)
            elif '.kiro/hooks/' in file or 'hooks/' in file:
                categories['hooks'].append(file)
            else:
                categories['other'].append(file)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def create_slack_message(self, git_info: Dict[str, Any], status_info: Dict[str, List[str]]) -> Dict[str, Any]:
        """Create a formatted Slack message for the development activity."""
        
        # Combine all changed files
        all_files = []
        all_files.extend(status_info.get('modified', []))
        all_files.extend(status_info.get('added', []))
        all_files.extend(status_info.get('deleted', []))
        
        # If we have git info, use those files instead
        if git_info.get('changed_files'):
            all_files = git_info['changed_files']
        
        # Categorize changes
        categorized = self.categorize_changes(all_files)
        
        # Determine activity type and emoji
        activity_emoji = "🔧"
        activity_type = "Development Activity"
        
        if categorized.get('core'):
            activity_emoji = "⚙️"
            activity_type = "Core System Update"
        elif categorized.get('templates'):
            activity_emoji = "📝"
            activity_type = "Template Enhancement"
        elif categorized.get('analytics'):
            activity_emoji = "📊"
            activity_type = "Analytics Update"
        elif categorized.get('hooks'):
            activity_emoji = "🪝"
            activity_type = "Agent Hooks Update"
        elif categorized.get('tests'):
            activity_emoji = "🧪"
            activity_type = "Testing Update"
        
        # Build the message blocks
        blocks = []
        
        # Header
        author_name = git_info.get('author_name', 'Developer')
        commit_message = git_info.get('commit_message', 'Recent development activity')
        
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{activity_emoji} {activity_type}",
                "emoji": True
            }
        })
        
        # Main info section
        main_text = f"*👤 Developer:* {author_name}\n"
        main_text += f"*📝 Changes:* {commit_message}\n"
        
        if git_info.get('commit_date'):
            try:
                commit_dt = datetime.fromisoformat(git_info['commit_date'].replace(' ', 'T'))
                formatted_date = commit_dt.strftime('%m/%d/%Y at %I:%M %p')
                main_text += f"*⏰ Timestamp:* {formatted_date}"
            except:
                main_text += f"*⏰ Timestamp:* {git_info['commit_date']}"
        else:
            main_text += f"*⏰ Timestamp:* {datetime.now().strftime('%m/%d/%Y at %I:%M %p')}"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": main_text
            }
        })
        
        # File changes summary
        total_files = len(all_files)
        if total_files > 0:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📁 Files Changed:* {total_files} files"
                }
            })
            
            # Categorized changes
            if categorized:
                category_text = "*🗂️ Change Categories:*\n"
                category_emojis = {
                    'core': '⚙️',
                    'templates': '📝',
                    'analytics': '📊',
                    'hooks': '🪝',
                    'tests': '🧪',
                    'docs': '📚',
                    'config': '⚙️',
                    'scripts': '🔧',
                    'examples': '💡',
                    'api': '🌐',
                    'other': '📄'
                }
                
                for category, files in categorized.items():
                    emoji = category_emojis.get(category, '📄')
                    category_text += f"• {emoji} {category.title()}: {len(files)} files\n"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": category_text.strip()
                    }
                })
            
            # Show some key files (limit to avoid message being too long)
            key_files = []
            for category in ['core', 'templates', 'analytics', 'hooks', 'api']:
                if category in categorized:
                    key_files.extend(categorized[category][:2])  # Max 2 files per category
            
            if key_files:
                files_text = "*🔍 Key Files:*\n"
                for file in key_files[:8]:  # Limit to 8 files total
                    # Shorten long file paths
                    display_file = file
                    if len(file) > 50:
                        parts = file.split('/')
                        if len(parts) > 2:
                            display_file = f"{parts[0]}/.../{parts[-1]}"
                    files_text += f"• `{display_file}`\n"
                
                if len(all_files) > 8:
                    files_text += f"• ... and {len(all_files) - 8} more files\n"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": files_text.strip()
                    }
                })
        
        # Add divider
        blocks.append({"type": "divider"})
        
        # Action buttons
        buttons = [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📊 View Dashboard",
                    "emoji": True
                },
                "action_id": "view_dashboard",
                "value": "dashboard"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🔍 View Changes",
                    "emoji": True
                },
                "action_id": "view_changes",
                "value": "git_diff"
            }
        ]
        
        blocks.append({
            "type": "actions",
            "elements": buttons
        })
        
        # Footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"DevSync AI • {datetime.now().strftime('%I:%M %p')}"
                }
            ]
        })
        
        # Fallback text for notifications
        fallback_text = f"{activity_type} by {author_name}: {commit_message}"
        
        return {
            "blocks": blocks,
            "text": fallback_text
        }
    
    async def send_notification(self) -> bool:
        """Send the development activity notification."""
        try:
            print("🔍 Analyzing development activity...")
            
            # Get git information
            git_info = self.get_git_info()
            status_info = self.get_git_status()
            
            if not git_info and not any(status_info.values()):
                print("ℹ️ No recent development activity found")
                return False
            
            print(f"📊 Found activity: {git_info.get('commit_message', 'Working directory changes')}")
            
            # Create Slack message
            message = self.create_slack_message(git_info, status_info)
            
            # Send to Slack
            if not self.slack_client:
                print("⚠️ Slack client not configured - cannot send notification")
                print("📝 Message that would have been sent:")
                print(json.dumps(message, indent=2))
                return False
            
            # Get channel from environment or use default
            channel = os.getenv('SLACK_CHANNEL', 'general')
            
            print(f"📤 Sending notification to #{channel}...")
            
            result = await self.slack_client.send_message(
                channel=channel,
                blocks=message['blocks'],
                text=message['text']
            )
            
            if result.get('ok'):
                print("✅ Development activity notification sent successfully!")
                return True
            else:
                print(f"❌ Failed to send notification: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending development activity notification: {e}")
            return False


async def main():
    """Main function to run the development activity notification."""
    print("🚀 DevSync AI - Development Activity Notification")
    print("=" * 50)
    
    analyzer = DevActivityAnalyzer()
    success = await analyzer.send_notification()
    
    if success:
        print("\n✨ Notification sent successfully!")
    else:
        print("\n⚠️ Notification could not be sent")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)