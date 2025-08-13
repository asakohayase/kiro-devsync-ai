"""Block Kit component builders for common Slack message patterns."""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .status_indicators import StatusIndicatorSystem, default_status_system


class HeaderSize(Enum):
    """Header size options."""
    LARGE = "large"
    MEDIUM = "medium"
    SMALL = "small"


class ButtonStyle(Enum):
    """Button style options."""
    PRIMARY = "primary"
    DANGER = "danger"
    DEFAULT = "default"


@dataclass
class ActionButton:
    """Action button configuration."""
    label: str
    action_id: Optional[str] = None
    url: Optional[str] = None
    value: Optional[str] = None
    style: ButtonStyle = ButtonStyle.DEFAULT
    confirm: Optional[Dict[str, Any]] = None


@dataclass
class HeaderConfig:
    """Header configuration."""
    title: str
    status: Optional[str] = None
    status_context: str = "general"
    timestamp: Optional[datetime] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    actions: Optional[List[ActionButton]] = None
    size: HeaderSize = HeaderSize.MEDIUM


@dataclass
class SectionConfig:
    """Section configuration."""
    text: Optional[str] = None
    fields: Optional[Dict[str, str]] = None
    accessory: Optional[Dict[str, Any]] = None
    markdown: bool = True


@dataclass
class ContextConfig:
    """Context configuration."""
    elements: List[str]
    images: Optional[List[Dict[str, str]]] = None


class BlockKitBuilder:
    """Builder for common Block Kit patterns."""
    
    def __init__(self, status_system: Optional[StatusIndicatorSystem] = None):
        """Initialize with status indicator system."""
        self.status_system = status_system or default_status_system
    
    def build_header(self, config: Union[HeaderConfig, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build header block with title, status, and optional elements."""
        if isinstance(config, dict):
            config = HeaderConfig(**config)
        
        blocks = []
        
        # Main header with status indicator
        header_text = config.title
        if config.status:
            indicator = self.status_system.get_indicator_by_string(config.status, config.status_context)
            header_text = f"{indicator.emoji} {config.title}"
        
        # Create header block
        header_block = {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": header_text,
                "emoji": True
            }
        }
        blocks.append(header_block)
        
        # Subtitle section
        subtitle_parts = []
        if config.subtitle:
            subtitle_parts.append(f"_{config.subtitle}_")
        
        if config.timestamp:
            formatted_time = config.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
            subtitle_parts.append(f"🕐 {formatted_time}")
        
        if config.status and config.status_context != "general":
            indicator = self.status_system.get_indicator_by_string(config.status, config.status_context)
            subtitle_parts.append(f"{indicator.emoji} {indicator.text}")
        
        if subtitle_parts:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": " • ".join(subtitle_parts)
                }
            })
        
        # Description if provided
        if config.description:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": config.description
                }
            })
        
        # Action buttons
        if config.actions:
            action_elements = []
            for action in config.actions:
                if isinstance(action, dict):
                    # Convert dict to ActionButton
                    action_data = {
                        'label': action.get('label', 'Action'),
                        'action_id': action.get('action_id'),
                        'url': action.get('url'),
                        'value': action.get('value'),
                        'style': ButtonStyle(action.get('style', 'default')) if action.get('style') else ButtonStyle.DEFAULT,
                        'confirm': action.get('confirm')
                    }
                    action = ActionButton(**action_data)
                
                button = self._build_button(action)
                action_elements.append(button)
            
            if action_elements:
                blocks.append({
                    "type": "actions",
                    "elements": action_elements
                })
        
        return blocks
    
    def build_section(self, config: Union[SectionConfig, Dict[str, Any]]) -> Dict[str, Any]:
        """Build section block with rich text and field support."""
        if isinstance(config, dict):
            config = SectionConfig(**config)
        
        section = {"type": "section"}
        
        # Main text content
        if config.text:
            section["text"] = {
                "type": "mrkdwn" if config.markdown else "plain_text",
                "text": config.text
            }
            if not config.markdown:
                section["text"]["emoji"] = True
        
        # Fields (side-by-side layout)
        if config.fields:
            field_elements = []
            for key, value in config.fields.items():
                field_elements.append({
                    "type": "mrkdwn",
                    "text": f"*{key}:*\n{value}"
                })
            section["fields"] = field_elements
        
        # Accessory element
        if config.accessory:
            section["accessory"] = config.accessory
        
        return section
    
    def build_rich_text_section(self, content: str, **formatting) -> Dict[str, Any]:
        """Build section with rich text formatting support."""
        # Process markdown-like formatting
        processed_content = self._process_rich_text(content, **formatting)
        
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": processed_content
            }
        }
    
    def build_field_group(self, fields: Dict[str, str], columns: int = 2) -> Dict[str, Any]:
        """Build section with grouped fields in columns."""
        field_elements = []
        
        for key, value in fields.items():
            # Format value based on type
            if isinstance(value, bool):
                formatted_value = "✅ Yes" if value else "❌ No"
            elif isinstance(value, (int, float)):
                formatted_value = str(value)
            elif isinstance(value, list):
                formatted_value = f"{len(value)} items"
            else:
                formatted_value = str(value)
            
            field_elements.append({
                "type": "mrkdwn",
                "text": f"*{key}:*\n{formatted_value}"
            })
        
        return {
            "type": "section",
            "fields": field_elements
        }
    
    def build_action_buttons(self, actions: List[Union[ActionButton, Dict[str, Any]]]) -> Dict[str, Any]:
        """Build action block with multiple buttons."""
        elements = []
        
        for action in actions:
            if isinstance(action, dict):
                # Convert dict keys to ActionButton format
                action_data = {
                    'label': action.get('label', 'Action'),
                    'action_id': action.get('action_id'),
                    'url': action.get('url'),
                    'value': action.get('value'),
                    'style': ButtonStyle(action.get('style', 'default')) if action.get('style') else ButtonStyle.DEFAULT,
                    'confirm': action.get('confirm')
                }
                action = ActionButton(**action_data)
            
            button = self._build_button(action)
            elements.append(button)
        
        return {
            "type": "actions",
            "elements": elements
        }
    
    def build_context(self, config: Union[ContextConfig, Dict[str, Any]]) -> Dict[str, Any]:
        """Build context block with metadata and small text."""
        if isinstance(config, dict):
            config = ContextConfig(**config)
        
        elements = []
        
        # Add text elements
        for element in config.elements:
            elements.append({
                "type": "mrkdwn",
                "text": element
            })
        
        # Add image elements if provided
        if config.images:
            for image in config.images:
                elements.append({
                    "type": "image",
                    "image_url": image["url"],
                    "alt_text": image.get("alt_text", "Image")
                })
        
        return {
            "type": "context",
            "elements": elements
        }
    
    def build_divider(self) -> Dict[str, Any]:
        """Build divider block for visual separation."""
        return {"type": "divider"}
    
    def build_conditional_divider(self, condition: bool) -> Optional[Dict[str, Any]]:
        """Build divider only if condition is true."""
        return self.build_divider() if condition else None
    
    def build_user_mention(self, username: str) -> str:
        """Format username as Slack mention."""
        if username and username != 'Unknown' and not username.startswith('<@'):
            return f"<@{username}>"
        return username or "Unassigned"
    
    def build_channel_reference(self, channel: str) -> str:
        """Format channel as Slack reference."""
        if channel and not channel.startswith('<#'):
            return f"<#{channel}>"
        return channel
    
    def build_url_link(self, url: str, text: str) -> str:
        """Format URL as Slack link."""
        if url and url != '#':
            return f"<{url}|{text}>"
        return text
    
    def build_code_block(self, code: str, language: str = "") -> str:
        """Format code block with optional language."""
        if language:
            return f"```{language}\n{code}\n```"
        return f"`{code}`"
    
    def build_timestamp_context(self, timestamp: Optional[datetime] = None, 
                              author: Optional[str] = None, 
                              additional_info: Optional[List[str]] = None) -> Dict[str, Any]:
        """Build context block with timestamp and metadata."""
        elements = []
        
        # Timestamp
        if not timestamp:
            timestamp = datetime.now()
        formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        elements.append(f"🕐 {formatted_time}")
        
        # Author
        if author:
            elements.append(f"👤 {self.build_user_mention(author)}")
        
        # Additional info
        if additional_info:
            elements.extend(additional_info)
        
        return self.build_context(ContextConfig(elements=elements))
    
    def build_progress_section(self, completed: int, total: int, 
                             label: str = "Progress", 
                             show_bar: bool = True) -> Dict[str, Any]:
        """Build section with progress indicator."""
        indicator = self.status_system.create_progress_indicator(completed, total)
        
        text_parts = [f"*{label}:* {indicator.emoji} {indicator.text}"]
        
        if show_bar:
            text_parts.append(f"`{indicator.description}`")
        
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(text_parts)
            }
        }
    
    def build_status_section(self, status: str, context: str = "general", 
                           additional_text: Optional[str] = None) -> Dict[str, Any]:
        """Build section with status indicator."""
        indicator = self.status_system.get_indicator_by_string(status, context)
        
        text = f"*Status:* {indicator.emoji} {indicator.text}"
        if additional_text:
            text += f"\n{additional_text}"
        
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text
            }
        }
    
    def _build_button(self, action: ActionButton) -> Dict[str, Any]:
        """Build individual button element."""
        button = {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": action.label,
                "emoji": True
            }
        }
        
        # Action ID for interactive responses
        if action.action_id:
            button["action_id"] = action.action_id
        
        # URL for external links
        if action.url:
            button["url"] = action.url
        
        # Value payload
        if action.value:
            button["value"] = action.value
        
        # Button style
        if action.style != ButtonStyle.DEFAULT:
            button["style"] = action.style.value
        
        # Confirmation dialog for destructive actions
        if action.confirm:
            button["confirm"] = action.confirm
        
        return button
    
    def _process_rich_text(self, content: str, **formatting) -> str:
        """Process rich text formatting options."""
        # Apply user mentions
        if formatting.get('mentions'):
            for username in formatting['mentions']:
                content = content.replace(f"@{username}", self.build_user_mention(username))
        
        # Apply channel references
        if formatting.get('channels'):
            for channel in formatting['channels']:
                content = content.replace(f"#{channel}", self.build_channel_reference(channel))
        
        # Apply URL links
        if formatting.get('links'):
            for url, text in formatting['links'].items():
                content = content.replace(text, self.build_url_link(url, text))
        
        return content
    
    def create_confirmation_dialog(self, title: str, text: str, 
                                 confirm_text: str = "Yes", 
                                 deny_text: str = "Cancel") -> Dict[str, Any]:
        """Create confirmation dialog for destructive actions."""
        return {
            "title": {
                "type": "plain_text",
                "text": title
            },
            "text": {
                "type": "mrkdwn",
                "text": text
            },
            "confirm": {
                "type": "plain_text",
                "text": confirm_text
            },
            "deny": {
                "type": "plain_text",
                "text": deny_text
            }
        }


# Global default instance
default_builder = BlockKitBuilder()