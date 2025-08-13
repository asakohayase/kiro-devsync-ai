"""Base template class for Slack message templates."""

from abc import abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime

from .message_formatter import MessageFormatter, SlackMessage, TemplateConfig
from .status_indicators import StatusIndicatorSystem, StatusType
from .exceptions import DataValidationError, FormattingError


class SlackMessageTemplate(MessageFormatter):
    """Abstract base class for all Slack message templates."""
    
    # Define required fields that subclasses must specify
    REQUIRED_FIELDS: List[str] = []
    
    def __init__(self, config: Optional[TemplateConfig] = None, 
                 status_system: Optional[StatusIndicatorSystem] = None):
        """Initialize template with configuration."""
        super().__init__(config, status_system)
    
    def format_message(self, data: Dict[str, Any]) -> SlackMessage:
        """Format message with error handling and accessibility features."""
        try:
            # Validate required data
            validated_data = self.validate_data(data, self.REQUIRED_FIELDS)
            
            # Create message blocks
            blocks = self._create_message_blocks(validated_data)
            
            # Add branding if configured
            blocks = self.add_branding(blocks)
            
            # Add timestamp context
            blocks.append(self.create_timestamp_context())
            
            # Generate fallback text for accessibility
            fallback_text = self.ensure_accessibility(blocks)
            
            # Create final message
            message = SlackMessage(
                blocks=blocks,
                text=fallback_text,
                thread_ts=validated_data.get('thread_ts'),
                channel=validated_data.get('channel'),
                metadata={
                    'template_type': self.__class__.__name__,
                    'created_at': datetime.now().isoformat(),
                    'config': {
                        'team_id': self.config.team_id,
                        'interactive_elements': self.config.interactive_elements
                    }
                }
            )
            
            self.logger.info(f"Successfully formatted {self.__class__.__name__} message")
            return message
            
        except Exception as e:
            # Handle any formatting errors gracefully
            return self.handle_formatting_error(e, data)
    
    @abstractmethod
    def _create_message_blocks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create the main message blocks. Must be implemented by subclasses."""
        pass
    
    def _create_header_section(self, title: str, status: Optional[StatusType] = None, 
                              subtitle: Optional[str] = None) -> List[Dict[str, Any]]:
        """Create header section with optional status and subtitle."""
        blocks = [self.create_header_block(title, status)]
        
        if subtitle:
            blocks.append(self.create_section_block(f"_{subtitle}_"))
        
        return blocks
    
    def _create_summary_fields(self, data: Dict[str, Any], field_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Create summary fields section from data mapping."""
        fields = {}
        for key, display_name in field_mapping.items():
            if key in data and data[key] is not None:
                value = data[key]
                # Format different value types appropriately
                if isinstance(value, bool):
                    fields[display_name] = "✅ Yes" if value else "❌ No"
                elif isinstance(value, (int, float)):
                    fields[display_name] = str(value)
                elif isinstance(value, list):
                    fields[display_name] = f"{len(value)} items"
                else:
                    fields[display_name] = str(value)
        
        return self.create_fields_section(fields) if fields else None
    
    def _create_action_buttons(self, actions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Create action buttons if interactive elements are enabled."""
        if not self.config.interactive_elements or not actions:
            return None
        
        buttons = []
        for action in actions:
            button = self.create_button_element(
                text=action.get('text', 'Action'),
                action_id=action.get('action_id', 'default_action'),
                value=action.get('value', ''),
                style=action.get('style'),
                url=action.get('url')
            )
            buttons.append(button)
        
        return self.create_actions_block(buttons)
    
    def _format_user_mention(self, username: str) -> str:
        """Format username as Slack mention or fallback."""
        if username and username != 'Unknown':
            return f"<@{username}>" if not username.startswith('@') else username
        return "Unassigned"
    
    def _format_url_link(self, url: str, text: str) -> str:
        """Format URL as Slack link or fallback."""
        if url and url != '#':
            return f"<{url}|{text}>"
        return text
    
    def _get_priority_indicator(self, priority: str) -> str:
        """Get priority indicator emoji and text."""
        priority_map = {
            'critical': '🚨 Critical',
            'high': '🔴 High', 
            'medium': '🟡 Medium',
            'low': '🟢 Low'
        }
        return priority_map.get(priority.lower(), f"⚪ {priority}")
    
    def _truncate_text(self, text: str, max_length: int = 150) -> str:
        """Truncate text with ellipsis if too long."""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."