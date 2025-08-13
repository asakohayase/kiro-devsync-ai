# Base Message Template System Documentation

## Overview

The DevSync AI Base Message Template System provides a comprehensive foundation for creating consistent, accessible, and feature-rich Slack notifications. Built with Python dataclasses, type hints, and proper error handling, it ensures high code quality and maintainability.

## Architecture

### Core Components

#### SlackMessageTemplate (Abstract Base Class)
The main abstract base class that all templates inherit from. Provides:
- Common formatting methods
- Emoji and icon constants
- Color scheme definitions
- Block Kit helper methods
- Template inheritance support
- Error handling for missing data
- Fallback text generation

#### Configuration Classes
- **MessageMetadata**: Tracking and analytics data
- **TeamBranding**: Team-specific customization
- **ChannelConfig**: Channel-specific formatting
- **UserPreferences**: User preference overrides
- **AccessibilityOptions**: Accessibility support

#### Constants and Enums
- **EmojiConstants**: Consistent emoji usage
- **IconConstants**: Slack icon references
- **ColorScheme**: Color palette definitions
- **MessagePriority**: Priority levels

## Key Features

### 1. Consistent Formatting
- Standardized header/footer structure
- Unified block creation methods
- Consistent spacing and layout
- Brand-compliant styling

### 2. Team Branding
```python
branding = create_team_branding(
    "DevOps Team",
    primary_color="#ff6b35",
    footer_text="DevOps Team • 24/7 Operations",
    custom_emojis={"success": ":custom_check:"},
    date_format="%B %d, %Y at %I:%M %p"
)
```

### 3. Accessibility Support
```python
accessibility = create_accessibility_options(
    screen_reader_optimized=True,
    high_contrast=True,
    alt_text_required=True,
    color_blind_friendly=True
)
```

### 4. Responsive Design
- Mobile-optimized layouts
- Compact mode for space-constrained channels
- Adaptive content based on screen size
- Progressive disclosure of information

### 5. Interactive Elements
```python
# Create interactive buttons
button = template.create_button(
    "Approve Changes", 
    "approve_action", 
    value="change_123",
    style="primary",
    emoji="✅"
)
```

### 6. Threading Support
```python
# Enable message threading
template.set_thread_ts("1234567890.123456")
```

### 7. Analytics Tracking
```python
# Add custom analytics data
template.add_analytics_data("user_action", "button_click")
template.add_analytics_data("feature_flag", "new_ui_enabled")

# Get analytics data
analytics = template.get_analytics_data()
```

## Creating Custom Templates

### Basic Template Structure

```python
from devsync_ai.core.base_template import SlackMessageTemplate, EmojiConstants

class MyCustomTemplate(SlackMessageTemplate):
    """Custom template example."""
    
    def _validate_data(self) -> None:
        """Validate template-specific data."""
        if not self.data.get('required_field'):
            raise ValueError("required_field is required")
    
    def _build_message_content(self) -> None:
        """Build template-specific content."""
        title = self.data.get('title', 'Default Title')
        description = self.data.get('description', '')
        
        # Add content sections
        self.add_section_block(f"*{title}*\n{description}")
        
        # Add fields if needed
        if self.data.get('show_details'):
            fields = [
                {"type": "mrkdwn", "text": "*Status:* Active"},
                {"type": "mrkdwn", "text": "*Priority:* High"}
            ]
            self.add_fields_block(fields)
        
        # Add action buttons
        self._add_custom_actions()
    
    def _add_custom_actions(self) -> None:
        """Add custom action buttons."""
        buttons = [
            self.create_button("Primary Action", "primary_action", 
                             style="primary", emoji="🚀"),
            self.create_button("Secondary Action", "secondary_action")
        ]
        self.add_actions_block(buttons)
    
    def _get_header_text(self) -> str:
        """Get header text."""
        return "Custom Template"
    
    def _get_header_emoji(self) -> str:
        """Get header emoji."""
        return EmojiConstants.INFO
```

### Using the Template

```python
# Basic usage
data = {
    "required_field": "value",
    "title": "My Custom Message",
    "description": "This is a custom message",
    "show_details": True
}

template = MyCustomTemplate(data)
message = template.get_message()

# With configuration
branding = create_team_branding("My Team")
channel_config = create_channel_config("C123456", "notifications")
user_prefs = create_user_preferences("U123456", compact_mode=True)

template = MyCustomTemplate(
    data,
    team_branding=branding,
    channel_config=channel_config,
    user_preferences=user_prefs
)
```

## Block Kit Helper Methods

### Section Blocks
```python
# Simple text section
self.add_section_block("*Bold text* and regular text")

# Section with accessory
accessory = {"type": "image", "image_url": "...", "alt_text": "..."}
self.add_section_block("Text with image", accessory=accessory)
```

### Field Blocks
```python
fields = [
    {"type": "mrkdwn", "text": "*Field 1:* Value 1"},
    {"type": "mrkdwn", "text": "*Field 2:* Value 2"}
]
self.add_fields_block(fields)
```

### Action Blocks
```python
buttons = [
    self.create_button("Button 1", "action_1", style="primary"),
    self.create_button("Button 2", "action_2", url="https://example.com")
]
self.add_actions_block(buttons)
```

### Other Blocks
```python
# Header block
self.add_header_block("Header Text", "🎉")

# Divider
self.add_divider_block()

# Context (footer)
self.add_context_block(["Context item 1", "Context item 2"])

# Image
self.add_image_block("https://example.com/image.png", "Alt text", "Title")
```

## Configuration Options

### Team Branding
```python
branding = TeamBranding(
    team_name="Engineering Team",
    primary_color="#1f77b4",
    logo_url="https://company.com/logo.png",
    footer_text="Engineering Team • Building the future",
    custom_emojis={
        "success": ":white_check_mark:",
        "warning": ":warning:",
        "error": ":x:"
    },
    timezone="America/New_York",
    date_format="%B %d, %Y at %I:%M %p"
)
```

### Channel Configuration
```python
channel_config = ChannelConfig(
    channel_id="C1234567890",
    channel_name="dev-notifications",
    threading_enabled=True,
    mentions_enabled=True,
    compact_mode=False,
    max_blocks=50,
    custom_formatting={
        "show_timestamps": True,
        "show_avatars": False
    }
)
```

### User Preferences
```python
user_prefs = UserPreferences(
    user_id="U1234567890",
    timezone="Europe/London",
    date_format="%d/%m/%Y %H:%M",
    compact_mode=True,
    emoji_style="unicode",  # unicode, slack, custom
    notification_level="detailed",  # minimal, normal, detailed
    accessibility_mode=True
)
```

### Accessibility Options
```python
accessibility = AccessibilityOptions(
    high_contrast=True,
    large_text=False,
    screen_reader_optimized=True,
    reduced_motion=False,
    alt_text_required=True,
    color_blind_friendly=True
)
```

## Helper Methods

### Text Formatting
```python
# Truncate long text
truncated = template._truncate_text("Very long text...", max_length=100)

# Format lists
formatted = template._format_list(
    ["Item 1", "Item 2", "Item 3"], 
    max_items=2, 
    show_count=True
)

# Create progress bars
progress = template._create_progress_bar(7, 10)  # "███████░░░ 7/10 (70%)"
```

### Time Formatting
```python
# Format timestamps according to user preferences
formatted_time = template._format_timestamp(datetime.now())
```

### Color and Emoji Management
```python
# Get team-customized colors
color = template._get_color("primary")  # Returns team's primary color

# Get team-customized emojis
emoji = template._get_emoji("success", "✅")  # Returns custom or default
```

## Error Handling

### Validation Errors
```python
def _validate_data(self) -> None:
    """Validate required data."""
    required_fields = ['title', 'status', 'assignee']
    for field in required_fields:
        if not self.data.get(field):
            raise ValueError(f"{field} is required")
```

### Error Recovery
```python
# Check for errors
if template.has_errors():
    errors = template.get_errors()
    print(f"Template errors: {errors}")

# Check for warnings
if template.has_warnings():
    warnings = template.get_warnings()
    print(f"Template warnings: {warnings}")

# Templates with errors still generate error messages
message = template.get_message()  # Returns error message blocks
```

## Analytics and Tracking

### Message Metadata
```python
metadata = MessageMetadata(
    template_name="deployment_notification",
    template_version="2.1",
    user_id="U1234567890",
    channel_id="C0987654321",
    priority=MessagePriority.HIGH,
    tags=["deployment", "production", "success"]
)
```

### Custom Analytics Data
```python
# Add tracking data
template.add_analytics_data("deployment_id", "deploy-456")
template.add_analytics_data("environment", "production")
template.add_analytics_data("duration_seconds", 120)

# Retrieve analytics
analytics = template.get_analytics_data()
```

### Analytics Data Structure
```python
{
    "template_name": "deployment_notification",
    "template_version": "2.1",
    "created_at": "2025-08-12T15:30:00Z",
    "priority": "high",
    "tags": ["deployment", "production"],
    "block_count": 8,
    "has_errors": false,
    "has_warnings": false,
    "custom_data": {
        "deployment_id": "deploy-456",
        "environment": "production",
        "duration_seconds": 120
    }
}
```

## A/B Testing Support

### Template Variants
```python
# Create different template variants
class StandardTemplate(SlackMessageTemplate):
    # Standard implementation
    pass

class EnhancedTemplate(SlackMessageTemplate):
    # Enhanced implementation with more features
    pass

# Use with template factory for A/B testing
factory.register_template("notification", TemplateConfig(
    name="standard_v1",
    template_class=StandardTemplate,
    weight=70  # 70% of users
))

factory.register_template("notification", TemplateConfig(
    name="enhanced_v1", 
    template_class=EnhancedTemplate,
    weight=30  # 30% of users
))
```

## Performance Considerations

### Block Limits
- Slack limits messages to 50 blocks
- Templates automatically enforce limits
- Warnings generated when limits approached

### Caching
- Template results can be cached
- Cache keys based on data content
- TTL-based cache expiration

### Memory Usage
- Efficient block creation
- Minimal object overhead
- Garbage collection friendly

## Best Practices

### 1. Template Design
- Keep templates focused and single-purpose
- Use consistent naming conventions
- Implement proper validation
- Provide meaningful error messages

### 2. Content Guidelines
- Use clear, concise language
- Implement progressive disclosure
- Prioritize important information
- Consider mobile users

### 3. Accessibility
- Always provide alt text for images
- Use high contrast colors
- Support screen readers
- Test with accessibility tools

### 4. Performance
- Minimize block count
- Cache expensive operations
- Use efficient data structures
- Monitor template performance

### 5. Testing
- Test with various data scenarios
- Validate error handling
- Check accessibility compliance
- Test on different devices

## Migration Guide

### From Legacy Templates
```python
# Old way (legacy SlackTemplateBase)
class OldTemplate(SlackTemplateBase):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self._build_message()

# New way (SlackMessageTemplate)
class NewTemplate(SlackMessageTemplate):
    def _validate_data(self):
        # Add validation
        pass
    
    def _build_message_content(self):
        # Build content using helper methods
        pass
```

### Benefits of Migration
- Better error handling
- Accessibility support
- Analytics tracking
- Team branding
- Configuration flexibility
- Mobile optimization

## Troubleshooting

### Common Issues

**Template not rendering:**
- Check validation errors with `template.get_errors()`
- Verify required data fields
- Check block structure validity

**Missing styling:**
- Verify team branding configuration
- Check color scheme definitions
- Validate emoji constants

**Accessibility issues:**
- Enable accessibility options
- Provide alt text for images
- Test with screen readers

**Performance problems:**
- Check block count limits
- Optimize data processing
- Enable caching where appropriate

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Templates will log detailed information
template = MyTemplate(data)
```

## Future Enhancements

- **Rich Media Support**: Enhanced image and video handling
- **Internationalization**: Multi-language template support
- **Advanced Analytics**: Detailed engagement metrics
- **Template Marketplace**: Shared template repository
- **Visual Editor**: GUI-based template creation
- **Real-time Updates**: Live template modification