"""SlackMessageFormatterFactory for routing messages to appropriate formatters."""

import logging
from typing import Dict, List, Any, Optional, Type, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib

from .message_formatter import MessageFormatter, SlackMessage, TemplateConfig
from .exceptions import DataValidationError, FormattingError
from ..formatters.pr_message_formatter import PRMessageFormatter
from ..formatters.jira_message_formatter import JIRAMessageFormatter
from ..formatters.standup_message_formatter import StandupMessageFormatter
from ..formatters.blocker_message_formatter import BlockerMessageFormatter


class MessageType(Enum):
    """Supported message types."""
    PR_UPDATE = "pr_update"
    PR_BATCH = "pr_batch"
    JIRA_UPDATE = "jira_update"
    JIRA_BATCH = "jira_batch"
    STANDUP = "standup"
    BLOCKER = "blocker"
    CUSTOM = "custom"


@dataclass
class FormatterOptions:
    """Options for message formatting."""
    batch: bool = False
    interactive: bool = True
    accessibility_mode: bool = False
    threading_enabled: bool = True
    experimental_features: bool = False
    ab_test_variant: Optional[str] = None
    custom_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChannelConfig:
    """Channel-specific configuration."""
    channel_id: str
    formatting_style: str = "default"  # default, minimal, rich
    interactive_elements: bool = True
    threading_enabled: bool = True
    custom_branding: Dict[str, Any] = field(default_factory=dict)
    feature_flags: Dict[str, bool] = field(default_factory=dict)


@dataclass
class TeamConfig:
    """Team-specific configuration."""
    team_id: str
    default_formatting: str = "rich"
    emoji_set: Dict[str, str] = field(default_factory=dict)
    color_scheme: Dict[str, str] = field(default_factory=dict)
    branding: Dict[str, Any] = field(default_factory=dict)
    feature_flags: Dict[str, bool] = field(default_factory=dict)
    ab_test_groups: Dict[str, str] = field(default_factory=dict)


@dataclass
class ProcessingResult:
    """Result of message processing pipeline."""
    success: bool
    message: Optional[SlackMessage] = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    formatter_used: Optional[str] = None
    cache_hit: bool = False


class SlackMessageFormatterFactory:
    """Factory for creating and managing Slack message formatters."""
    
    def __init__(self, config: Optional[TemplateConfig] = None):
        """Initialize factory with configuration."""
        self.config = config or TemplateConfig(team_id="default")
        self.logger = logging.getLogger(__name__)
        
        # Formatter registry
        self._formatters: Dict[MessageType, Type[MessageFormatter]] = {}
        self._formatter_instances: Dict[str, MessageFormatter] = {}
        
        # Configuration storage
        self._team_configs: Dict[str, TeamConfig] = {}
        self._channel_configs: Dict[str, ChannelConfig] = {}
        
        # Caching
        self._message_cache: Dict[str, SlackMessage] = {}
        self._cache_ttl: Dict[str, datetime] = {}
        
        # A/B testing
        self._ab_tests: Dict[str, Dict[str, Any]] = {}
        
        # Performance metrics
        self._metrics: Dict[str, Any] = {
            'total_messages': 0,
            'cache_hits': 0,
            'errors': 0,
            'formatter_usage': {},
            'processing_times': []
        }
        
        # Register default formatters
        self._register_default_formatters()
    
    def _register_default_formatters(self):
        """Register default message formatters."""
        self.register_formatter(MessageType.PR_UPDATE, PRMessageFormatter)
        self.register_formatter(MessageType.PR_BATCH, PRMessageFormatter)
        self.register_formatter(MessageType.JIRA_UPDATE, JIRAMessageFormatter)
        self.register_formatter(MessageType.JIRA_BATCH, JIRAMessageFormatter)
        self.register_formatter(MessageType.STANDUP, StandupMessageFormatter)
        self.register_formatter(MessageType.BLOCKER, BlockerMessageFormatter)
    
    def register_formatter(self, message_type: MessageType, formatter_class: Type[MessageFormatter]):
        """Register a formatter for a specific message type."""
        self._formatters[message_type] = formatter_class
        self.logger.info(f"Registered formatter {formatter_class.__name__} for {message_type.value}")
    
    def register_custom_formatter(self, type_name: str, formatter_class: Type[MessageFormatter]):
        """Register a custom formatter with a string type name."""
        custom_type = MessageType.CUSTOM
        self._formatters[f"custom_{type_name}"] = formatter_class
        self.logger.info(f"Registered custom formatter {formatter_class.__name__} for {type_name}")
    
    def configure_team(self, team_config: TeamConfig):
        """Configure team-specific settings."""
        self._team_configs[team_config.team_id] = team_config
        self.logger.info(f"Configured team settings for {team_config.team_id}")
    
    def configure_channel(self, channel_config: ChannelConfig):
        """Configure channel-specific settings."""
        self._channel_configs[channel_config.channel_id] = channel_config
        self.logger.info(f"Configured channel settings for {channel_config.channel_id}")
    
    def setup_ab_test(self, test_name: str, variants: Dict[str, Dict[str, Any]]):
        """Setup A/B test configuration."""
        self._ab_tests[test_name] = variants
        self.logger.info(f"Setup A/B test '{test_name}' with {len(variants)} variants")
    
    def format_message(self, 
                      message_type: Union[str, MessageType],
                      data: Dict[str, Any],
                      channel: Optional[str] = None,
                      team_id: Optional[str] = None,
                      options: Optional[FormatterOptions] = None) -> ProcessingResult:
        """
        Format a message using the appropriate formatter.
        
        This is the main entry point for the message processing pipeline.
        """
        start_time = datetime.now()
        
        try:
            # Step 1: Data validation and sanitization
            validated_data = self._validate_and_sanitize_data(data, message_type)
            
            # Step 2: Formatter selection
            formatter = self._select_formatter(message_type, channel, team_id, options)
            
            # Step 3: Check cache
            cache_key = self._generate_cache_key(message_type, validated_data, options)
            cached_message = self._get_cached_message(cache_key)
            if cached_message:
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                self._update_metrics(True, processing_time, formatter.__class__.__name__)
                return ProcessingResult(
                    success=True,
                    message=cached_message,
                    processing_time_ms=processing_time,
                    formatter_used=formatter.__class__.__name__,
                    cache_hit=True
                )
            
            # Step 4: Rich formatting with Block Kit
            message = formatter.format_message(validated_data)
            
            # Step 5: Apply channel/team customizations
            message = self._apply_customizations(message, channel, team_id, options)
            
            # Step 6: Final message validation
            validation_warnings = self._validate_final_message(message)
            
            # Step 7: Cache the result
            self._cache_message(cache_key, message)
            
            # Update metrics
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_metrics(False, processing_time, formatter.__class__.__name__)
            
            return ProcessingResult(
                success=True,
                message=message,
                warnings=validation_warnings,
                processing_time_ms=processing_time,
                formatter_used=formatter.__class__.__name__,
                cache_hit=False
            )
            
        except Exception as e:
            # Step 8: Error handling and logging
            return self._handle_formatting_error(e, message_type, data, start_time)
    
    def _validate_and_sanitize_data(self, data: Dict[str, Any], message_type: Union[str, MessageType]) -> Dict[str, Any]:
        """Validate and sanitize input data."""
        if not isinstance(data, dict):
            raise DataValidationError("Data must be a dictionary")
        
        # Deep copy to avoid modifying original data
        sanitized_data = json.loads(json.dumps(data, default=str))
        
        # Type-specific validation
        if isinstance(message_type, str):
            message_type = MessageType(message_type)
        
        # Add validation rules based on message type
        required_fields = self._get_required_fields(message_type)
        missing_fields = [field for field in required_fields if field not in sanitized_data]
        
        if missing_fields:
            self.logger.warning(f"Missing required fields for {message_type.value}: {missing_fields}")
            # Add placeholder values
            for field in missing_fields:
                sanitized_data[field] = self._get_placeholder_value(field)
        
        return sanitized_data
    
    def _select_formatter(self, 
                         message_type: Union[str, MessageType],
                         channel: Optional[str],
                         team_id: Optional[str],
                         options: Optional[FormatterOptions]) -> MessageFormatter:
        """Select appropriate formatter based on type and configuration."""
        
        # Convert string to enum if needed
        if isinstance(message_type, str):
            try:
                message_type = MessageType(message_type)
            except ValueError:
                # Check for custom formatters
                custom_key = f"custom_{message_type}"
                if custom_key in self._formatters:
                    formatter_class = self._formatters[custom_key]
                else:
                    raise FormattingError(f"Unknown message type: {message_type}")
            else:
                formatter_class = self._formatters.get(message_type)
        else:
            formatter_class = self._formatters.get(message_type)
        
        if not formatter_class:
            raise FormattingError(f"No formatter registered for {message_type}")
        
        # Create formatter instance key
        config = self._build_formatter_config(channel, team_id, options)
        instance_key = f"{formatter_class.__name__}_{hash(str(config.__dict__))}"
        
        # Get or create formatter instance
        if instance_key not in self._formatter_instances:
            self._formatter_instances[instance_key] = formatter_class(config=config)
        
        return self._formatter_instances[instance_key]
    
    def _build_formatter_config(self, 
                               channel: Optional[str],
                               team_id: Optional[str],
                               options: Optional[FormatterOptions]) -> TemplateConfig:
        """Build formatter configuration from team/channel settings."""
        
        # Start with base config
        config = TemplateConfig(team_id=team_id or self.config.team_id)
        
        # Apply team configuration
        if team_id and team_id in self._team_configs:
            team_config = self._team_configs[team_id]
            config.branding.update(team_config.branding)
            config.emoji_set.update(team_config.emoji_set)
            config.color_scheme.update(team_config.color_scheme)
        
        # Apply channel configuration
        if channel and channel in self._channel_configs:
            channel_config = self._channel_configs[channel]
            config.interactive_elements = channel_config.interactive_elements
            config.threading_enabled = channel_config.threading_enabled
            if channel_config.custom_branding:
                config.branding.update(channel_config.custom_branding)
        
        # Apply options
        if options:
            config.interactive_elements = options.interactive
            config.accessibility_mode = options.accessibility_mode
            config.threading_enabled = options.threading_enabled
            
            # Apply A/B test variant
            if options.ab_test_variant:
                self._apply_ab_test_config(config, options.ab_test_variant)
        
        return config
    
    def _apply_ab_test_config(self, config: TemplateConfig, variant: str):
        """Apply A/B test configuration variant."""
        for test_name, variants in self._ab_tests.items():
            if variant in variants:
                variant_config = variants[variant]
                # Apply variant-specific configuration
                if 'branding' in variant_config:
                    config.branding.update(variant_config['branding'])
                if 'interactive_elements' in variant_config:
                    config.interactive_elements = variant_config['interactive_elements']
                self.logger.debug(f"Applied A/B test variant '{variant}' for test '{test_name}'")
    
    def _apply_customizations(self, 
                            message: SlackMessage,
                            channel: Optional[str],
                            team_id: Optional[str],
                            options: Optional[FormatterOptions]) -> SlackMessage:
        """Apply channel and team-specific customizations to the message."""
        
        # Apply channel-specific styling
        if channel and channel in self._channel_configs:
            channel_config = self._channel_configs[channel]
            
            # Modify message based on formatting style
            if channel_config.formatting_style == "minimal":
                message = self._apply_minimal_styling(message)
            elif channel_config.formatting_style == "rich":
                message = self._apply_rich_styling(message)
        
        # Apply feature flags
        if options and options.experimental_features:
            message = self._apply_experimental_features(message)
        
        return message
    
    def _apply_minimal_styling(self, message: SlackMessage) -> SlackMessage:
        """Apply minimal styling by reducing visual elements."""
        # Remove dividers and reduce visual complexity
        filtered_blocks = []
        for block in message.blocks:
            if block.get('type') != 'divider':
                filtered_blocks.append(block)
        
        message.blocks = filtered_blocks
        return message
    
    def _apply_rich_styling(self, message: SlackMessage) -> SlackMessage:
        """Apply rich styling with enhanced visual elements."""
        # Add additional visual elements if not present
        # This is where you could add extra formatting, colors, etc.
        return message
    
    def _apply_experimental_features(self, message: SlackMessage) -> SlackMessage:
        """Apply experimental features to the message."""
        # Add experimental Block Kit elements or formatting
        # This could include new block types, enhanced interactivity, etc.
        return message
    
    def _validate_final_message(self, message: SlackMessage) -> List[str]:
        """Validate the final message and return warnings."""
        warnings = []
        
        # Check message size
        message_size = len(json.dumps(message.blocks))
        if message_size > 50000:  # Slack's limit is ~50KB
            warnings.append(f"Message size ({message_size} bytes) approaching Slack limit")
        
        # Check block count
        if len(message.blocks) > 50:  # Slack's limit is 50 blocks
            warnings.append(f"Message has {len(message.blocks)} blocks (limit is 50)")
        
        # Check for required fallback text
        if not message.text or len(message.text) < 10:
            warnings.append("Message fallback text is too short")
        
        # Validate block structure
        for i, block in enumerate(message.blocks):
            if not isinstance(block, dict) or 'type' not in block:
                warnings.append(f"Block {i} has invalid structure")
        
        return warnings
    
    def _generate_cache_key(self, 
                           message_type: Union[str, MessageType],
                           data: Dict[str, Any],
                           options: Optional[FormatterOptions]) -> str:
        """Generate cache key for message."""
        key_data = {
            'type': str(message_type),
            'data_hash': hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest(),
            'options': options.__dict__ if options else {}
        }
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    
    def _get_cached_message(self, cache_key: str) -> Optional[SlackMessage]:
        """Get cached message if still valid."""
        if cache_key in self._message_cache:
            # Check TTL (5 minutes default)
            if cache_key in self._cache_ttl:
                if datetime.now() < self._cache_ttl[cache_key]:
                    return self._message_cache[cache_key]
                else:
                    # Expired, remove from cache
                    del self._message_cache[cache_key]
                    del self._cache_ttl[cache_key]
        return None
    
    def _cache_message(self, cache_key: str, message: SlackMessage, ttl_minutes: int = 5):
        """Cache message with TTL."""
        self._message_cache[cache_key] = message
        self._cache_ttl[cache_key] = datetime.now() + timedelta(minutes=ttl_minutes)
        
        # Clean up old cache entries (keep last 1000)
        if len(self._message_cache) > 1000:
            oldest_keys = sorted(self._cache_ttl.keys(), key=lambda k: self._cache_ttl[k])[:100]
            for key in oldest_keys:
                self._message_cache.pop(key, None)
                self._cache_ttl.pop(key, None)
    
    def _handle_formatting_error(self, 
                                error: Exception,
                                message_type: Union[str, MessageType],
                                data: Dict[str, Any],
                                start_time: datetime) -> ProcessingResult:
        """Handle formatting errors with graceful degradation."""
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        self._metrics['errors'] += 1
        
        error_message = str(error)
        self.logger.error(f"Formatting error for {message_type}: {error_message}", exc_info=True)
        
        # Try to create fallback message
        try:
            fallback_message = self._create_fallback_message(error_message, data)
            return ProcessingResult(
                success=False,
                message=fallback_message,
                error=error_message,
                warnings=["Used fallback formatting due to error"],
                processing_time_ms=processing_time,
                formatter_used="fallback"
            )
        except Exception as fallback_error:
            self.logger.error(f"Fallback formatting also failed: {fallback_error}")
            return ProcessingResult(
                success=False,
                error=f"Formatting failed: {error_message}. Fallback also failed: {fallback_error}",
                processing_time_ms=processing_time
            )
    
    def _create_fallback_message(self, error_message: str, data: Dict[str, Any]) -> SlackMessage:
        """Create a simple fallback message when formatting fails."""
        
        # Extract basic information
        title = "Message Formatting Error"
        description = f"Unable to format message properly: {error_message}"
        
        # Try to extract some useful info from data
        data_summary = []
        if isinstance(data, dict):
            for key, value in list(data.items())[:5]:  # Show first 5 fields
                if isinstance(value, (str, int, float, bool)):
                    data_summary.append(f"• {key}: {value}")
        
        fallback_text = f"{title}\n{description}"
        if data_summary:
            fallback_text += f"\nData: {', '.join(data_summary)}"
        
        # Create simple blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⚠️ Message Formatting Error"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Error:* {error_message}\n\n*Raw data available for debugging.*"
                }
            }
        ]
        
        return SlackMessage(
            blocks=blocks,
            text=fallback_text,
            metadata={"error": True, "fallback": True}
        )
    
    def _get_required_fields(self, message_type: MessageType) -> List[str]:
        """Get required fields for a message type."""
        field_map = {
            MessageType.PR_UPDATE: ['pr'],
            MessageType.PR_BATCH: ['prs'],
            MessageType.JIRA_UPDATE: ['ticket'],
            MessageType.JIRA_BATCH: ['tickets'],
            MessageType.STANDUP: ['date', 'team'],
            MessageType.BLOCKER: ['blocker']
        }
        return field_map.get(message_type, [])
    
    def _get_placeholder_value(self, field_name: str) -> Any:
        """Get placeholder value for missing field."""
        placeholders = {
            'pr': {'number': 0, 'title': 'Unknown PR'},
            'prs': [],
            'ticket': {'key': 'UNKNOWN', 'summary': 'Unknown ticket'},
            'tickets': [],
            'date': datetime.now().strftime('%Y-%m-%d'),
            'team': 'Unknown Team',
            'blocker': {'id': 'UNKNOWN', 'title': 'Unknown blocker'}
        }
        return placeholders.get(field_name, f'Missing {field_name}')
    
    def _update_metrics(self, cache_hit: bool, processing_time: float, formatter_name: str):
        """Update performance metrics."""
        self._metrics['total_messages'] += 1
        if cache_hit:
            self._metrics['cache_hits'] += 1
        
        self._metrics['processing_times'].append(processing_time)
        if len(self._metrics['processing_times']) > 1000:
            self._metrics['processing_times'] = self._metrics['processing_times'][-1000:]
        
        if formatter_name not in self._metrics['formatter_usage']:
            self._metrics['formatter_usage'][formatter_name] = 0
        self._metrics['formatter_usage'][formatter_name] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        processing_times = self._metrics['processing_times']
        
        return {
            'total_messages': self._metrics['total_messages'],
            'cache_hit_rate': (self._metrics['cache_hits'] / max(1, self._metrics['total_messages'])) * 100,
            'error_rate': (self._metrics['errors'] / max(1, self._metrics['total_messages'])) * 100,
            'avg_processing_time_ms': sum(processing_times) / max(1, len(processing_times)),
            'formatter_usage': self._metrics['formatter_usage'].copy(),
            'cache_size': len(self._message_cache)
        }
    
    def clear_cache(self):
        """Clear message cache."""
        self._message_cache.clear()
        self._cache_ttl.clear()
        self.logger.info("Message cache cleared")
    
    def get_registered_formatters(self) -> Dict[str, str]:
        """Get list of registered formatters."""
        return {
            message_type.value: formatter_class.__name__
            for message_type, formatter_class in self._formatters.items()
        }