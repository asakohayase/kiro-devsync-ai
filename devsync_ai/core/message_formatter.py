"""Core message formatter for converting raw data to Slack Block Kit JSON."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import logging

from .exceptions import DataValidationError, FormattingError
from .status_indicators import StatusIndicatorSystem, StatusType, UrgencyLevel, default_status_system


logger = logging.getLogger(__name__)


@dataclass
class SlackMessage:
    """Represents a complete Slack message with blocks and metadata."""
    blocks: List[Dict[str, Any]]
    text: str  # Fallback text for accessibility
    thread_ts: Optional[str] = None
    channel: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TemplateConfig:
    """Configuration for template customization."""
    team_id: str
    branding: Dict[str, Any] = field(default_factory=dict)
    emoji_set: Dict[str, str] = field(default_factory=dict)
    color_scheme: Dict[str, str] = field(default_factory=dict)
    interactive_elements: bool = True
    accessibility_mode: bool = False
    threading_enabled: bool = True


class MessageFormatter(ABC):
    """Abstract base class for Slack message formatters."""
    
    def __init__(self, config: Optional[TemplateConfig] = None, 
                 status_system: Optional[StatusIndicatorSystem] = None):
        """Initialize formatter with configuration and status system."""
        self.config = config or TemplateConfig(team_id="default")
        self.status_system = status_system or default_status_system
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def format_message(self, data: Dict[str, Any]) -> SlackMessage:
        """Format raw data into a Slack message. Must be implemented by subclasses."""
        pass
    
    def validate_data(self, data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        """Validate input data and handle missing fields gracefully."""
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        
        if missing_fields:
            self.logger.warning(f"Missing required fields: {missing_fields}")
            # Add placeholder values for missing fields
            for field in missing_fields:
                data[field] = self._get_placeholder_value(field)
        
        return data
    
    def _get_placeholder_value(self, field_name: str) -> Any:
        """Get placeholder value for missing data fields."""
        placeholders = {
            'title': 'Untitled',
            'description': 'No description provided',
            'author': 'Unknown',
            'status': 'Unknown',
            'priority': 'Medium',
            'assignee': 'Unassigned',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'url': '#',
            'team': 'Unknown Team',
            'team_members': [],
            'stats': {},
            'action_items': []
        }
        return placeholders.get(field_name, f'Missing {field_name}')
    
    def create_header_block(self, title: str, status_type: Optional[StatusType] = None) -> Dict[str, Any]:
        """Create a header block with optional status indicator."""
        header_text = title
        
        if status_type:
            indicator = self.status_system.get_status_indicator(status_type)
            header_text = f"{indicator.emoji} {title}"
        
        return {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": header_text,
                "emoji": True
            }
        }
    
    def create_section_block(self, text: str, accessory: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a section block with optional accessory element."""
        block = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text
            }
        }
        
        if accessory:
            block["accessory"] = accessory
        
        return block
    
    def create_context_block(self, elements: List[str]) -> Dict[str, Any]:
        """Create a context block with multiple text elements."""
        return {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": element
                } for element in elements
            ]
        }
    
    def create_divider_block(self) -> Dict[str, Any]:
        """Create a divider block for visual separation."""
        return {"type": "divider"}
    
    def create_button_element(self, text: str, action_id: str, value: str = "", 
                            style: Optional[str] = None, url: Optional[str] = None) -> Dict[str, Any]:
        """Create a button element for interactive actions."""
        button = {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": text,
                "emoji": True
            },
            "action_id": action_id
        }
        
        if value:
            button["value"] = value
        if style in ["primary", "danger"]:
            button["style"] = style
        if url:
            button["url"] = url
        
        return button
    
    def create_actions_block(self, buttons: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create an actions block with multiple buttons."""
        return {
            "type": "actions",
            "elements": buttons
        }
    
    def create_fields_section(self, fields: Dict[str, str]) -> Dict[str, Any]:
        """Create a section with multiple fields in two columns."""
        field_elements = []
        for key, value in fields.items():
            field_elements.append({
                "type": "mrkdwn",
                "text": f"*{key}:*\n{value}"
            })
        
        return {
            "type": "section",
            "fields": field_elements
        }
    
    def add_branding(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add team branding elements to message blocks."""
        if not self.config.branding:
            return blocks
        
        # Add team logo/emoji to header if present
        if blocks and blocks[0].get("type") == "header" and "logo_emoji" in self.config.branding:
            header_text = blocks[0]["text"]["text"]
            blocks[0]["text"]["text"] = f"{self.config.branding['logo_emoji']} {header_text}"
        
        # Add team name context if configured
        if "team_name" in self.config.branding:
            team_context = self.create_context_block([
                f"📋 {self.config.branding['team_name']}"
            ])
            blocks.append(team_context)
        
        return blocks
    
    def ensure_accessibility(self, blocks: List[Dict[str, Any]]) -> str:
        """Generate fallback text for accessibility compliance."""
        fallback_parts = []
        
        for block in blocks:
            if block.get("type") == "header":
                fallback_parts.append(f"HEADER: {block['text']['text']}")
            elif block.get("type") == "section":
                if "text" in block:
                    # Strip markdown formatting for plain text
                    text = block["text"]["text"].replace("*", "").replace("_", "").replace("`", "")
                    fallback_parts.append(text)
                if "fields" in block:
                    for field in block["fields"]:
                        text = field["text"].replace("*", "").replace("_", "").replace("`", "")
                        fallback_parts.append(text)
            elif block.get("type") == "context":
                context_texts = []
                for element in block.get("elements", []):
                    if element.get("type") == "mrkdwn":
                        text = element["text"].replace("*", "").replace("_", "").replace("`", "")
                        context_texts.append(text)
                if context_texts:
                    fallback_parts.append(" | ".join(context_texts))
        
        return "\n".join(fallback_parts)
    
    def handle_formatting_error(self, error: Exception, data: Dict[str, Any]) -> SlackMessage:
        """Handle formatting errors with graceful fallback."""
        self.logger.error(f"Formatting error: {error}")
        
        # Create simple fallback message
        fallback_blocks = [
            self.create_header_block("⚠️ Message Formatting Error"),
            self.create_section_block(
                f"Unable to format message properly. Raw data available.\n"
                f"Error: {str(error)}"
            )
        ]
        
        if self.config.accessibility_mode:
            # Include raw data in accessibility mode
            fallback_blocks.append(
                self.create_section_block(f"```{str(data)}```")
            )
        
        return SlackMessage(
            blocks=fallback_blocks,
            text=f"Message formatting error: {str(error)}",
            metadata={"error": True, "original_data": data}
        )
    
    def create_timestamp_context(self, timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """Create a context block with timestamp information."""
        if not timestamp:
            timestamp = datetime.now()
        
        formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        return self.create_context_block([f"🕐 {formatted_time}"])
    
    def create_progress_section(self, completed: int, total: int, label: str = "Progress") -> Dict[str, Any]:
        """Create a section showing progress with visual indicator."""
        indicator = self.status_system.create_progress_indicator(completed, total)
        
        return self.create_section_block(
            f"*{label}:* {indicator.emoji} {indicator.text}\n"
            f"`{indicator.description}`"
        )