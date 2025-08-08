import logging
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class SlackClientError(Exception):
    """Base exception for Slack client errors."""
    pass


class SlackAPIError(SlackClientError):
    """Exception raised for Slack API errors."""
    
    def __init__(self, error: str, response: Optional[Dict[str, Any]] = None):
        self.error = error
        self.response = response
        super().__init__(f"Slack API Error: {error}")


class SlackClient:
    """
    A production-ready Slack client for interacting with the Slack Web API.
    
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
        backoff_factor: float = 0.3,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the Slack client.
        
        Args:
            token: Slack bot token or user token
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            backoff_factor: Backoff factor for retries
            logger: Optional logger instance
        """
        self.token = token
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Default headers
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "SlackClient/1.0"
        })
    
    def _make_request(
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
        
        try:
            self.logger.debug(f"Making {method} request to {url}")
            
            if files:
                # For file uploads, don't set Content-Type header
                headers = {"Authorization": f"Bearer {self.token}"}
                response = self.session.request(
                    method=method,
                    url=url,
                    data=data,
                    files=files,
                    headers=headers,
                    timeout=self.timeout
                )
            else:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    timeout=self.timeout
                )
            
            response.raise_for_status()
            result = response.json()
            
            if not result.get("ok", False):
                error = result.get("error", "Unknown error")
                self.logger.error(f"Slack API error: {error}")
                raise SlackAPIError(error, result)
            
            self.logger.debug(f"Request successful: {endpoint}")
            return result
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            raise SlackClientError(f"Request failed: {e}") from e
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON response: {e}")
            raise SlackClientError(f"Invalid JSON response: {e}") from e
    
    def send_message(
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
        
        return self._make_request("POST", "chat.postMessage", data)
    
    def update_message(
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
        
        return self._make_request("POST", "chat.update", data)
    
    def delete_message(self, channel: str, ts: str) -> Dict[str, Any]:
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
        
        return self._make_request("POST", "chat.delete", data)
    
    def get_channel_history(
        self,
        channel: str,
        count: int = 100,
        latest: Optional[str] = None,
        oldest: Optional[str] = None,
        inclusive: bool = False
    ) -> Dict[str, Any]:
        """
        Get channel message history.
        
        Args:
            channel: Channel ID or name
            count: Number of messages to return
            latest: End of time range of messages
            oldest: Start of time range of messages
            inclusive: Include messages with latest or oldest timestamp
            
        Returns:
            API response containing messages
        """
        data = {
            "channel": channel,
            "count": count,
            "inclusive": inclusive
        }
        
        if latest:
            data["latest"] = latest
        if oldest:
            data["oldest"] = oldest
        
        return self._make_request("GET", "channels.history", data)
    
    def list_channels(
        self,
        exclude_archived: bool = True,
        exclude_members: bool = False
    ) -> Dict[str, Any]:
        """
        List all channels.
        
        Args:
            exclude_archived: Exclude archived channels
            exclude_members: Exclude member information
            
        Returns:
            API response containing channel list
        """
        data = {
            "exclude_archived": exclude_archived,
            "exclude_members": exclude_members
        }
        
        return self._make_request("GET", "channels.list", data)
    
    def get_channel_info(self, channel: str) -> Dict[str, Any]:
        """
        Get information about a channel.
        
        Args:
            channel: Channel ID or name
            
        Returns:
            API response containing channel information
        """
        data = {"channel": channel}
        return self._make_request("GET", "channels.info", data)
    
    def create_channel(
        self,
        name: str,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new channel.
        
        Args:
            name: Channel name
            validate: Whether to validate the name
            
        Returns:
            API response containing new channel information
        """
        data = {
            "name": name,
            "validate": validate
        }
        
        return self._make_request("POST", "channels.create", data)
    
    def join_channel(self, channel: str) -> Dict[str, Any]:
        """
        Join a channel.
        
        Args:
            channel: Channel ID or name
            
        Returns:
            API response
        """
        data = {"channel": channel}
        return self._make_request("POST", "channels.join", data)
    
    def leave_channel(self, channel: str) -> Dict[str, Any]:
        """
        Leave a channel.
        
        Args:
            channel: Channel ID or name
            
        Returns:
            API response
        """
        data = {"channel": channel}
        return self._make_request("POST", "channels.leave", data)
    
    def invite_to_channel(
        self,
        channel: str,
        user: str
    ) -> Dict[str, Any]:
        """
        Invite a user to a channel.
        
        Args:
            channel: Channel ID or name
            user: User ID to invite
            
        Returns:
            API response
        """
        data = {
            "channel": channel,
            "user": user
        }
        
        return self._make_request("POST", "channels.invite", data)
    
    def upload_file(
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
            files["file"] = open(file_path, "rb")
            if not filename:
                filename = file_path.split("/")[-1]
        elif file_content:
            if not filename:
                filename = "file"
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
        
        try:
            return self._make_request("POST", "files.upload", data, files)
        finally:
            # Close file if we opened it
            if file_path and "file" in files:
                files["file"].close()
    
    def get_user_info(self, user: str) -> Dict[str, Any]:
        """
        Get information about a user.
        
        Args:
            user: User ID
            
        Returns:
            API response containing user information
        """
        data = {"user": user}
        return self._make_request("GET", "users.info", data)
    
    def list_users(
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
        
        return self._make_request("GET", "users.list", data)
    
    def set_user_presence(self, presence: str) -> Dict[str, Any]:
        """
        Set user presence.
        
        Args:
            presence: Presence state ('auto' or 'away')
            
        Returns:
            API response
        """
        if presence not in ["auto", "away"]:
            raise ValueError("Presence must be 'auto' or 'away'")
        
        data = {"presence": presence}
        return self._make_request("POST", "users.setPresence", data)
    
    def get_user_presence(self, user: str) -> Dict[str, Any]:
        """
        Get user presence information.
        
        Args:
            user: User ID
            
        Returns:
            API response containing presence information
        """
        data = {"user": user}
        return self._make_request("GET", "users.getPresence", data)
    
    def add_reaction(
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
        
        return self._make_request("POST", "reactions.add", data)
    
    def remove_reaction(
        self,
        channel: str,
        timestamp: str,
        name: str
    ) -> Dict[str, Any]:
        """
        Remove a reaction from a message.
        
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
        
        return self._make_request("POST", "reactions.remove", data)
    
    def test_auth(self) -> Dict[str, Any]:
        """
        Test authentication and get information about the authenticated user/bot.
        
        Returns:
            API response containing authentication information
        """
        return self._make_request("GET", "auth.test")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.session.close()
