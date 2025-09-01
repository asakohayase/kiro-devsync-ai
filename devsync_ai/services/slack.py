"""
Slack service for DevSync AI.
Provides Slack integration with proper error handling and async support.
"""

import logging
import json
import os
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import aiohttp
import asyncio
from urllib.parse import urlencode

from devsync_ai.config import settings


logger = logging.getLogger(__name__)


class SlackClientError(Exception):
    """Base exception for Slack client errors."""
    pass


class SlackAPIError(SlackClientError):
    """Exception raised for Slack API errors."""
    
    def __init__(self, error: str, response: Optional[Dict[str, Any]] = None):
        self.error = error
        self.response = response
        super().__init__(f"Slack API Error: {error}")


class AsyncSlackClient:
    """
    Async Slack client for interacting with the Slack Web API.
    
    This client provides methods for sending messages, managing channels,
    handling files, and other Slack operations with proper error handling,
    logging, and retry mechanisms.
    """
    
    BASE_URL = "https://slack.com/api"
    
    def __init__(
        self,
        token: str,
        timeout: int = 30,
        max_retries: int = 3,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the Slack client.
        
        Args:
            token: Slack bot token or user token
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            logger: Optional logger instance
        """
        self.token = token
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logger or logging.getLogger(__name__)
        
        # Default headers
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "DevSyncAI-SlackClient/1.0"
        }
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the Slack API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request data
            files: Files to upload
            
        Returns:
            API response as dictionary
            
        Raises:
            SlackAPIError: If the API returns an error
            SlackClientError: For other client errors
        """
        url = f"{self.BASE_URL}/{endpoint}"
        
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    if files:
                        # For file uploads, use multipart form data
                        form_data = aiohttp.FormData()
                        if data:
                            for key, value in data.items():
                                form_data.add_field(key, str(value))
                        
                        for key, file_data in files.items():
                            if isinstance(file_data, tuple):
                                filename, content = file_data
                                form_data.add_field(key, content, filename=filename)
                            else:
                                form_data.add_field(key, file_data)
                        
                        headers = {"Authorization": f"Bearer {self.token}"}
                        async with session.request(
                            method=method,
                            url=url,
                            data=form_data,
                            headers=headers
                        ) as response:
                            result = await response.json()
                    else:
                        async with session.request(
                            method=method,
                            url=url,
                            json=data,
                            headers=self.headers
                        ) as response:
                            result = await response.json()
                
                if not result.get("ok", False):
                    error = result.get("error", "Unknown error")
                    self.logger.error(f"Slack API error: {error}")
                    
                    # Retry on rate limit
                    if error == "rate_limited" and attempt < self.max_retries:
                        retry_after = result.get("retry_after", 1)
                        self.logger.info(f"Rate limited, retrying after {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    raise SlackAPIError(error, result)
                
                self.logger.debug(f"Request successful: {endpoint}")
                return result
                
            except aiohttp.ClientError as e:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                    continue
                
                self.logger.error(f"Request failed after {self.max_retries + 1} attempts: {e}")
                raise SlackClientError(f"Request failed: {e}") from e
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to decode JSON response: {e}")
                raise SlackClientError(f"Invalid JSON response: {e}") from e
        
        raise SlackClientError("Max retries exceeded")
    
    async def send_message(
        self,
        channel: str,
        text: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        thread_ts: Optional[str] = None,
        reply_broadcast: bool = False,
        unfurl_links: bool = True,
        unfurl_media: bool = True
    ) -> Dict[str, Any]:
        """
        Send a message to a Slack channel.
        
        Args:
            channel: Channel ID or name
            text: Message text
            blocks: Block kit blocks
            attachments: Message attachments
            thread_ts: Timestamp of thread to reply to
            reply_broadcast: Whether to broadcast thread reply
            unfurl_links: Whether to unfurl links
            unfurl_media: Whether to unfurl media
            
        Returns:
            API response containing message details
        """
        if not text and not blocks and not attachments:
            raise ValueError("Must provide text, blocks, or attachments")
        
        # Remove # from channel if present and not a channel ID
        if channel.startswith("#"):
            channel = channel[1:]
        
        data = {
            "channel": channel,
            "unfurl_links": unfurl_links,
            "unfurl_media": unfurl_media
        }
        
        if text:
            data["text"] = text
        if blocks:
            data["blocks"] = blocks
        if attachments:
            data["attachments"] = attachments
        if thread_ts:
            data["thread_ts"] = thread_ts
            data["reply_broadcast"] = reply_broadcast
        
        return await self._make_request("POST", "chat.postMessage", data)
    
    async def update_message(
        self,
        channel: str,
        ts: str,
        text: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing message.
        
        Args:
            channel: Channel ID or name
            ts: Timestamp of message to update
            text: New message text
            blocks: New block kit blocks
            attachments: New message attachments
            
        Returns:
            API response
        """
        data = {
            "channel": channel,
            "ts": ts
        }
        
        if text:
            data["text"] = text
        if blocks:
            data["blocks"] = blocks
        if attachments:
            data["attachments"] = attachments
        
        return await self._make_request("POST", "chat.update", data)
    
    async def delete_message(self, channel: str, ts: str) -> Dict[str, Any]:
        """
        Delete a message.
        
        Args:
            channel: Channel ID or name
            ts: Timestamp of message to delete
            
        Returns:
            API response
        """
        data = {
            "channel": channel,
            "ts": ts
        }
        
        return await self._make_request("POST", "chat.delete", data)
    
    async def get_channel_history(
        self,
        channel: str,
        limit: int = 100,
        latest: Optional[str] = None,
        oldest: Optional[str] = None,
        inclusive: bool = False
    ) -> Dict[str, Any]:
        """
        Get channel message history.
        
        Args:
            channel: Channel ID or name
            limit: Number of messages to return
            latest: End of time range of messages
            oldest: Start of time range of messages
            inclusive: Include messages with latest or oldest timestamp
            
        Returns:
            API response containing messages
        """
        data = {
            "channel": channel,
            "limit": limit,
            "inclusive": inclusive
        }
        
        if latest:
            data["latest"] = latest
        if oldest:
            data["oldest"] = oldest
        
        return await self._make_request("GET", "conversations.history", data)
    
    async def list_channels(
        self,
        exclude_archived: bool = True,
        types: str = "public_channel,private_channel"
    ) -> Dict[str, Any]:
        """
        List all channels.
        
        Args:
            exclude_archived: Exclude archived channels
            types: Channel types to include
            
        Returns:
            API response containing channel list
        """
        data = {
            "exclude_archived": exclude_archived,
            "types": types
        }
        
        return await self._make_request("GET", "conversations.list", data)
    
    async def get_channel_info(self, channel: str) -> Dict[str, Any]:
        """
        Get information about a channel.
        
        Args:
            channel: Channel ID or name
            
        Returns:
            API response containing channel information
        """
        data = {"channel": channel}
        return await self._make_request("GET", "conversations.info", data)
    
    async def join_channel(self, channel: str) -> Dict[str, Any]:
        """
        Join a channel.
        
        Args:
            channel: Channel ID or name
            
        Returns:
            API response
        """
        data = {"channel": channel}
        return await self._make_request("POST", "conversations.join", data)
    
    async def leave_channel(self, channel: str) -> Dict[str, Any]:
        """
        Leave a channel.
        
        Args:
            channel: Channel ID or name
            
        Returns:
            API response
        """
        data = {"channel": channel}
        return await self._make_request("POST", "conversations.leave", data)
    
    async def invite_to_channel(
        self,
        channel: str,
        users: Union[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Invite users to a channel.
        
        Args:
            channel: Channel ID or name
            users: User ID(s) to invite
            
        Returns:
            API response
        """
        if isinstance(users, list):
            users = ",".join(users)
        
        data = {
            "channel": channel,
            "users": users
        }
        
        return await self._make_request("POST", "conversations.invite", data)
    
    async def upload_file(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[bytes] = None,
        filename: Optional[str] = None,
        channels: Optional[Union[str, List[str]]] = None,
        title: Optional[str] = None,
        initial_comment: Optional[str] = None,
        filetype: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to Slack.
        
        Args:
            file_path: Path to file to upload
            file_content: File content as bytes
            filename: Name of the file
            channels: Channel(s) to share file in
            title: Title of the file
            initial_comment: Initial comment for the file
            filetype: File type
            
        Returns:
            API response containing file information
        """
        if not file_path and not file_content:
            raise ValueError("Must provide either file_path or file_content")
        
        data = {}
        files = {}
        
        if file_path:
            with open(file_path, "rb") as f:
                file_content = f.read()
            if not filename:
                filename = os.path.basename(file_path)
        
        if file_content and filename:
            files["file"] = (filename, file_content)
        
        if filename:
            data["filename"] = filename
        if channels:
            if isinstance(channels, list):
                data["channels"] = ",".join(channels)
            else:
                data["channels"] = channels
        if title:
            data["title"] = title
        if initial_comment:
            data["initial_comment"] = initial_comment
        if filetype:
            data["filetype"] = filetype
        
        return await self._make_request("POST", "files.upload", data, files)
    
    async def get_user_info(self, user: str) -> Dict[str, Any]:
        """
        Get information about a user.
        
        Args:
            user: User ID
            
        Returns:
            API response containing user information
        """
        data = {"user": user}
        return await self._make_request("GET", "users.info", data)
    
    async def list_users(
        self,
        cursor: Optional[str] = None,
        limit: int = 0,
        include_locale: bool = False
    ) -> Dict[str, Any]:
        """
        List all users in the workspace.
        
        Args:
            cursor: Pagination cursor
            limit: Maximum number of users to return
            include_locale: Include locale information
            
        Returns:
            API response containing user list
        """
        data = {
            "include_locale": include_locale
        }
        
        if cursor:
            data["cursor"] = cursor
        if limit > 0:
            data["limit"] = limit
        
        return await self._make_request("GET", "users.list", data)
    
    async def add_reaction(
        self,
        channel: str,
        timestamp: str,
        name: str
    ) -> Dict[str, Any]:
        """
        Add a reaction to a message.
        
        Args:
            channel: Channel ID
            timestamp: Message timestamp
            name: Reaction name (without colons)
            
        Returns:
            API response
        """
        data = {
            "channel": channel,
            "timestamp": timestamp,
            "name": name
        }
        
        return await self._make_request("POST", "reactions.add", data)
    
    async def test_auth(self) -> Dict[str, Any]:
        """
        Test authentication and get information about the authenticated user/bot.
        
        Returns:
            API response containing auth information
        """
        return await self._make_request("GET", "auth.test")


class SlackService:
    """
    High-level Slack service for DevSync AI.
    Provides convenient methods for common Slack operations.
    """
    
    def __init__(self):
        """Initialize the Slack service."""
        self.token = getattr(settings, 'slack_bot_token', None) or os.getenv("SLACK_BOT_TOKEN")
        self.client = None
        self._changelog_integration = None
        
        if self.token:
            self.client = AsyncSlackClient(self.token)
            logger.info("✅ Slack service initialized")
        else:
            logger.warning("⚠️ Slack bot token not found - Slack features disabled")
    
    @property
    def changelog_integration(self):
        """Get the changelog integration instance (lazy loading)."""
        if self._changelog_integration is None and self.client:
            from devsync_ai.core.changelog_slack_integration import ChangelogSlackIntegration
            self._changelog_integration = ChangelogSlackIntegration(self)
        return self._changelog_integration
    
    async def send_message(
        self,
        channel: str,
        text: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a message to a Slack channel.
        
        Args:
            channel: Channel ID or name
            text: Message text
            blocks: Block kit blocks
            **kwargs: Additional arguments for send_message
            
        Returns:
            API response or error dict
        """
        if not self.client:
            logger.warning("Slack client not available - message not sent")
            return {"ok": False, "error": "slack_not_configured"}
        
        try:
            result = await self.client.send_message(
                channel=channel,
                text=text,
                blocks=blocks,
                **kwargs
            )
            logger.info(f"✅ Slack message sent to #{channel}")
            return result
        except Exception as e:
            logger.error(f"❌ Failed to send Slack message: {e}")
            return {"ok": False, "error": str(e)}
    
    async def send_pr_notification(
        self,
        pr_data: Dict[str, Any],
        action: str,
        channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a PR notification to Slack.
        
        Args:
            pr_data: Pull request data
            action: PR action (opened, closed, etc.)
            channel: Channel to send to (defaults to configured channel)
            
        Returns:
            API response or error dict
        """
        if not self.client:
            return {"ok": False, "error": "slack_not_configured"}
        
        try:
            from devsync_ai.services.slack_templates import create_pr_status_message
            
            # Prepare data for template
            template_data = {
                "pr": pr_data,
                "action": action
            }
            
            # Generate message using template
            message_payload = create_pr_status_message(template_data)
            
            # Send message
            target_channel = channel or getattr(settings, 'slack_default_channel', None) or os.getenv("SLACK_CHANNEL", "general")
            
            result = await self.client.send_message(
                channel=target_channel,
                text=message_payload.get("text", f"PR {action}: {pr_data.get('title', 'Unknown')}"),
                blocks=message_payload.get("blocks")
            )
            
            logger.info(f"✅ PR notification sent for #{pr_data.get('number', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to send PR notification: {e}")
            return {"ok": False, "error": str(e)}
    
    async def send_standup_summary(
        self,
        standup_data: Dict[str, Any],
        channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a standup summary to Slack.
        
        Args:
            standup_data: Standup data
            channel: Channel to send to
            
        Returns:
            API response or error dict
        """
        if not self.client:
            return {"ok": False, "error": "slack_not_configured"}
        
        try:
            from devsync_ai.services.slack_templates import create_standup_message
            
            # Generate message using template
            message_payload = create_standup_message(standup_data)
            
            # Send message
            target_channel = channel or getattr(settings, 'slack_default_channel', None) or os.getenv("SLACK_CHANNEL", "general")
            
            result = await self.client.send_message(
                channel=target_channel,
                text=message_payload.get("text", "Daily Standup Summary"),
                blocks=message_payload.get("blocks")
            )
            
            logger.info("✅ Standup summary sent")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to send standup summary: {e}")
            return {"ok": False, "error": str(e)}
    
    async def send_changelog_notification(
        self,
        changelog_data: Dict[str, Any],
        distribution_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a changelog notification with advanced interactive elements.
        
        Args:
            changelog_data: The formatted changelog data
            distribution_config: Distribution configuration
            
        Returns:
            Distribution results
        """
        if not self.client or not self.changelog_integration:
            logger.warning("Slack changelog integration not available")
            return {"ok": False, "error": "slack_not_configured"}
        
        try:
            config = distribution_config or {}
            result = await self.changelog_integration.distribute_changelog(
                changelog_data, config
            )
            
            if result.get("successful_deliveries", 0) > 0:
                logger.info(f"✅ Changelog distributed to {result['successful_deliveries']} channels")
            
            if result.get("failed_deliveries", 0) > 0:
                logger.warning(f"⚠️ Failed to deliver to {result['failed_deliveries']} channels")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to send changelog notification: {e}")
            return {"ok": False, "error": str(e)}
    
    async def handle_changelog_interaction(
        self,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle interactive callbacks from changelog messages.
        
        Args:
            payload: Slack interaction payload
            
        Returns:
            Response for the interaction
        """
        if not self.changelog_integration:
            return {
                "response_type": "ephemeral",
                "text": "❌ Changelog integration not available"
            }
        
        try:
            return await self.changelog_integration.handle_interactive_callback(payload)
        except Exception as e:
            logger.error(f"❌ Failed to handle changelog interaction: {e}")
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error processing interaction: {str(e)}"
            }
    
    async def collect_changelog_feedback(
        self,
        message_ts: str,
        channel_id: str,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Collect and analyze feedback from a changelog message.
        
        Args:
            message_ts: Message timestamp
            channel_id: Channel ID
            time_window_hours: Time window for feedback collection
            
        Returns:
            Analyzed feedback data
        """
        if not self.changelog_integration:
            return {"success": False, "error": "changelog_integration_not_available"}
        
        try:
            from datetime import timedelta
            time_window = timedelta(hours=time_window_hours)
            
            result = await self.changelog_integration.collect_and_analyze_feedback(
                message_ts, channel_id, time_window
            )
            
            if result.get("success"):
                logger.info(f"✅ Collected feedback for message {message_ts}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to collect changelog feedback: {e}")
            return {"success": False, "error": str(e)}

    async def get_weekly_changelog_data(self, team_id: str, week_range: Dict[str, Any]) -> Dict[str, Any]:
        """Get Slack-specific data for weekly changelog generation."""
        if not self.client:
            return {"error": "slack_not_configured"}
        
        try:
            # This would collect Slack-specific metrics like:
            # - Message activity patterns
            # - Channel engagement metrics
            # - Team communication trends
            # For now, return placeholder data
            return {
                "team_id": team_id,
                "week_range": week_range,
                "slack_metrics": {
                    "message_count": 0,
                    "active_channels": [],
                    "engagement_score": 0.0
                }
            }
        except Exception as e:
            logger.error(f"❌ Failed to get Slack changelog data: {e}")
            return {"error": str(e)}
    
    async def setup_changelog_fallbacks(
        self,
        primary_channels: List[str],
        fallback_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Setup fallback mechanisms for changelog distribution.
        
        Args:
            primary_channels: Primary distribution channels
            fallback_config: Fallback configuration
            
        Returns:
            Fallback setup result
        """
        if not self.changelog_integration:
            return {"success": False, "error": "changelog_integration_not_available"}
        
        try:
            result = await self.changelog_integration.setup_fallback_mechanisms(
                primary_channels, fallback_config
            )
            
            if result.get("success"):
                logger.info("✅ Changelog fallback mechanisms configured")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to setup changelog fallbacks: {e}")
            return {"success": False, "error": str(e)}

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the Slack connection.
        
        Returns:
            Connection test result
        """
        if not self.client:
            return {"ok": False, "error": "slack_not_configured"}
        
        try:
            result = await self.client.test_auth()
            logger.info("✅ Slack connection test successful")
            return result
        except Exception as e:
            logger.error(f"❌ Slack connection test failed: {e}")
            return {"ok": False, "error": str(e)}