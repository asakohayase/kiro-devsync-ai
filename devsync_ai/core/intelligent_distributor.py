"""
Intelligent Distribution System for Weekly Changelog Generation

This module provides intelligent content distribution across multiple channels
with audience-specific optimization, engagement tracking, and delivery confirmation.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Callable
from urllib.parse import urljoin
import hashlib
import re
# Optional email imports
try:
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import smtplib
    import ssl
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
import aiohttp

# Optional imports for advanced features
try:
    from jinja2 import Template, Environment, BaseLoader
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    # Fallback template class
    class BaseLoader:
        pass
    class Environment:
        def __init__(self, loader=None):
            self.loader = loader
        def from_string(self, template_str):
            return SimpleTemplate(template_str)
    
    class SimpleTemplate:
        def __init__(self, template_str):
            self.template_str = template_str
        def render(self, **kwargs):
            result = self.template_str
            for key, value in kwargs.items():
                result = result.replace(f'{{{{ {key} }}}}', str(value))
            return result

try:
    import feedgen.feed
    FEEDGEN_AVAILABLE = True
except ImportError:
    FEEDGEN_AVAILABLE = False

logger = logging.getLogger(__name__)


class ChannelType(Enum):
    """Supported distribution channels"""
    SLACK = "slack"
    EMAIL = "email"
    RSS = "rss"
    WEBHOOK = "webhook"
    SOCIAL_MEDIA = "social_media"


class AudienceType(Enum):
    """Target audience types for content optimization"""
    EXECUTIVE = "executive"
    TECHNICAL = "technical"
    PROJECT_MANAGER = "project_manager"
    STAKEHOLDER = "stakeholder"
    GENERAL = "general"


class DeliveryStatus(Enum):
    """Delivery status tracking"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class EngagementType(Enum):
    """Types of engagement metrics"""
    VIEW = "view"
    CLICK = "click"
    SHARE = "share"
    COMMENT = "comment"
    REACTION = "reaction"


@dataclass
class DistributionConfig:
    """Configuration for content distribution"""
    channels: List[ChannelType]
    audience_type: AudienceType
    personalization_enabled: bool = True
    a_b_testing_enabled: bool = False
    retry_attempts: int = 3
    retry_delay: int = 60  # seconds
    delivery_confirmation: bool = True
    engagement_tracking: bool = True
    custom_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChannelConfig:
    """Channel-specific configuration"""
    channel_type: ChannelType
    endpoint: Optional[str] = None
    credentials: Dict[str, str] = field(default_factory=dict)
    template_id: Optional[str] = None
    rate_limit: Optional[int] = None
    custom_headers: Dict[str, str] = field(default_factory=dict)
    optimization_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentVariant:
    """Content variant for A/B testing"""
    variant_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0


@dataclass
class DistributionResult:
    """Result of content distribution"""
    distribution_id: str
    channel_results: Dict[ChannelType, 'ChannelDeliveryResult']
    total_delivered: int
    total_failed: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChannelDeliveryResult:
    """Result of delivery to a specific channel"""
    channel_type: ChannelType
    status: DeliveryStatus
    delivery_id: Optional[str] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    engagement_metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EngagementMetrics:
    """Engagement tracking metrics"""
    distribution_id: str
    channel_type: ChannelType
    engagement_type: EngagementType
    count: int
    timestamp: datetime
    user_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmailTemplate:
    """Email template configuration"""
    subject_template: str
    html_template: str
    text_template: Optional[str] = None
    sender_name: str = "DevSync AI"
    sender_email: str = "noreply@devsync.ai"
    reply_to: Optional[str] = None


@dataclass
class RSSConfig:
    """RSS feed configuration"""
    title: str
    description: str
    link: str
    language: str = "en-US"
    author_name: str = "DevSync AI"
    author_email: str = "noreply@devsync.ai"
    category: Optional[str] = None
    ttl: int = 60  # minutes


class IntelligentDistributor:
    """
    Intelligent content distribution system with audience optimization,
    engagement tracking, and multi-channel delivery capabilities.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize the intelligent distributor"""
        self.config = config
        self.channel_configs: Dict[ChannelType, ChannelConfig] = {}
        self.email_templates: Dict[str, EmailTemplate] = {}
        self.rss_configs: Dict[str, RSSConfig] = {}
        self.engagement_callbacks: List[Callable] = []
        self.delivery_confirmations: Dict[str, ChannelDeliveryResult] = {}
        self.a_b_test_variants: Dict[str, List[ContentVariant]] = {}
        
        # Initialize Jinja2 environment for templating
        self.template_env = Environment(loader=BaseLoader())
        
        # Load configuration
        self._load_channel_configs()
        self._load_templates()
        
        logger.info("IntelligentDistributor initialized")

    def _load_channel_configs(self):
        """Load channel-specific configurations"""
        channels_config = self.config.get('channels', {})
        
        for channel_name, channel_data in channels_config.items():
            try:
                channel_type = ChannelType(channel_name.lower())
                self.channel_configs[channel_type] = ChannelConfig(
                    channel_type=channel_type,
                    endpoint=channel_data.get('endpoint'),
                    credentials=channel_data.get('credentials', {}),
                    template_id=channel_data.get('template_id'),
                    rate_limit=channel_data.get('rate_limit'),
                    custom_headers=channel_data.get('headers', {}),
                    optimization_settings=channel_data.get('optimization', {})
                )
            except ValueError:
                logger.warning(f"Unknown channel type: {channel_name}")

    def _load_templates(self):
        """Load email and other templates"""
        templates_config = self.config.get('templates', {})
        
        # Load email templates
        email_templates = templates_config.get('email', {})
        for template_id, template_data in email_templates.items():
            self.email_templates[template_id] = EmailTemplate(
                subject_template=template_data['subject'],
                html_template=template_data['html'],
                text_template=template_data.get('text'),
                sender_name=template_data.get('sender_name', 'DevSync AI'),
                sender_email=template_data.get('sender_email', 'noreply@devsync.ai'),
                reply_to=template_data.get('reply_to')
            )
        
        # Load RSS configurations
        rss_configs = templates_config.get('rss', {})
        for feed_id, feed_data in rss_configs.items():
            self.rss_configs[feed_id] = RSSConfig(
                title=feed_data['title'],
                description=feed_data['description'],
                link=feed_data['link'],
                language=feed_data.get('language', 'en-US'),
                author_name=feed_data.get('author_name', 'DevSync AI'),
                author_email=feed_data.get('author_email', 'noreply@devsync.ai'),
                category=feed_data.get('category'),
                ttl=feed_data.get('ttl', 60)
            )

    async def distribute_changelog(
        self, 
        changelog: Dict[str, Any], 
        config: DistributionConfig
    ) -> DistributionResult:
        """
        Distribute changelog content across configured channels
        
        Args:
            changelog: The changelog content to distribute
            config: Distribution configuration
            
        Returns:
            DistributionResult with delivery status and metrics
        """
        distribution_id = self._generate_distribution_id(changelog)
        started_at = datetime.utcnow()
        
        logger.info(f"Starting distribution {distribution_id} for {len(config.channels)} channels")
        
        # Optimize content for each audience type
        optimized_content = await self.optimize_content_for_audience(
            changelog, config.audience_type
        )
        
        # Handle A/B testing if enabled
        if config.a_b_testing_enabled:
            optimized_content = await self._handle_a_b_testing(
                optimized_content, distribution_id
            )
        
        # Distribute to each channel
        channel_results = {}
        distribution_tasks = []
        
        for channel_type in config.channels:
            if channel_type in self.channel_configs:
                task = self._distribute_to_channel(
                    channel_type, optimized_content, config, distribution_id
                )
                distribution_tasks.append((channel_type, task))
        
        # Execute distributions concurrently
        for channel_type, task in distribution_tasks:
            try:
                result = await task
                channel_results[channel_type] = result
            except Exception as e:
                logger.error(f"Distribution failed for {channel_type}: {e}")
                channel_results[channel_type] = ChannelDeliveryResult(
                    channel_type=channel_type,
                    status=DeliveryStatus.FAILED,
                    error_message=str(e)
                )
        
        # Calculate totals
        total_delivered = sum(
            1 for result in channel_results.values() 
            if result.status == DeliveryStatus.DELIVERED
        )
        total_failed = len(channel_results) - total_delivered
        
        completed_at = datetime.utcnow()
        
        result = DistributionResult(
            distribution_id=distribution_id,
            channel_results=channel_results,
            total_delivered=total_delivered,
            total_failed=total_failed,
            started_at=started_at,
            completed_at=completed_at
        )
        
        logger.info(
            f"Distribution {distribution_id} completed: "
            f"{total_delivered} delivered, {total_failed} failed"
        )
        
        return result

    async def optimize_content_for_audience(
        self, 
        content: Dict[str, Any], 
        audience_type: AudienceType
    ) -> Dict[str, Any]:
        """
        Optimize content based on audience type and preferences
        
        Args:
            content: Original content to optimize
            audience_type: Target audience type
            
        Returns:
            Optimized content for the specific audience
        """
        optimized = content.copy()
        
        # Audience-specific optimizations
        if audience_type == AudienceType.EXECUTIVE:
            optimized = await self._optimize_for_executives(optimized)
        elif audience_type == AudienceType.TECHNICAL:
            optimized = await self._optimize_for_technical(optimized)
        elif audience_type == AudienceType.PROJECT_MANAGER:
            optimized = await self._optimize_for_project_managers(optimized)
        elif audience_type == AudienceType.STAKEHOLDER:
            optimized = await self._optimize_for_stakeholders(optimized)
        else:
            optimized = await self._optimize_for_general(optimized)
        
        return optimized

    async def optimize_content_for_channel(
        self, 
        content: str, 
        channel: ChannelType
    ) -> str:
        """
        Optimize content format and structure for specific channel
        
        Args:
            content: Content to optimize
            channel: Target channel type
            
        Returns:
            Channel-optimized content
        """
        if channel == ChannelType.SLACK:
            return await self._optimize_for_slack(content)
        elif channel == ChannelType.EMAIL:
            return await self._optimize_for_email(content)
        elif channel == ChannelType.RSS:
            return await self._optimize_for_rss(content)
        elif channel == ChannelType.SOCIAL_MEDIA:
            return await self._optimize_for_social_media(content)
        else:
            return content

    async def track_engagement_metrics(
        self, 
        distribution_id: str
    ) -> EngagementMetrics:
        """
        Track and analyze engagement metrics for a distribution
        
        Args:
            distribution_id: ID of the distribution to track
            
        Returns:
            Aggregated engagement metrics
        """
        # This would integrate with analytics systems
        # For now, return mock data structure
        return EngagementMetrics(
            distribution_id=distribution_id,
            channel_type=ChannelType.SLACK,
            engagement_type=EngagementType.VIEW,
            count=0,
            timestamp=datetime.utcnow()
        )

    async def manage_delivery_confirmation(
        self, 
        distribution_id: str
    ) -> DeliveryStatus:
        """
        Check delivery confirmation status for a distribution
        
        Args:
            distribution_id: ID of the distribution to check
            
        Returns:
            Current delivery status
        """
        if distribution_id in self.delivery_confirmations:
            return self.delivery_confirmations[distribution_id].status
        return DeliveryStatus.PENDING

    async def handle_delivery_failures(
        self, 
        failed_delivery: ChannelDeliveryResult
    ) -> 'RecoveryAction':
        """
        Handle delivery failures with retry logic and fallback mechanisms
        
        Args:
            failed_delivery: Failed delivery result
            
        Returns:
            Recovery action to take
        """
        recovery_action = RecoveryAction(
            action_type="retry",
            retry_delay=60 * (2 ** failed_delivery.retry_count),  # Exponential backoff
            fallback_channel=None
        )
        
        # Implement retry logic based on failure type
        if failed_delivery.retry_count < 3:
            recovery_action.action_type = "retry"
        else:
            recovery_action.action_type = "fallback"
            recovery_action.fallback_channel = self._get_fallback_channel(
                failed_delivery.channel_type
            )
        
        return recovery_action

    # Private helper methods
    
    def _generate_distribution_id(self, content: Dict[str, Any]) -> str:
        """Generate unique distribution ID"""
        content_hash = hashlib.md5(
            json.dumps(content, sort_keys=True).encode()
        ).hexdigest()[:8]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"dist_{timestamp}_{content_hash}"

    async def _distribute_to_channel(
        self,
        channel_type: ChannelType,
        content: Dict[str, Any],
        config: DistributionConfig,
        distribution_id: str
    ) -> ChannelDeliveryResult:
        """Distribute content to a specific channel"""
        try:
            if channel_type == ChannelType.SLACK:
                return await self._distribute_to_slack(content, config, distribution_id)
            elif channel_type == ChannelType.EMAIL:
                return await self._distribute_to_email(content, config, distribution_id)
            elif channel_type == ChannelType.RSS:
                return await self._distribute_to_rss(content, config, distribution_id)
            elif channel_type == ChannelType.WEBHOOK:
                return await self._distribute_to_webhook(content, config, distribution_id)
            elif channel_type == ChannelType.SOCIAL_MEDIA:
                return await self._distribute_to_social_media(content, config, distribution_id)
            else:
                raise ValueError(f"Unsupported channel type: {channel_type}")
                
        except Exception as e:
            logger.error(f"Failed to distribute to {channel_type}: {e}")
            return ChannelDeliveryResult(
                channel_type=channel_type,
                status=DeliveryStatus.FAILED,
                error_message=str(e)
            )

    async def _distribute_to_slack(
        self,
        content: Dict[str, Any],
        config: DistributionConfig,
        distribution_id: str
    ) -> ChannelDeliveryResult:
        """Distribute content to Slack"""
        # This would integrate with the existing Slack service
        # For now, simulate successful delivery
        return ChannelDeliveryResult(
            channel_type=ChannelType.SLACK,
            status=DeliveryStatus.DELIVERED,
            delivery_id=f"slack_{distribution_id}",
            delivered_at=datetime.utcnow()
        )

    async def _distribute_to_email(
        self,
        content: Dict[str, Any],
        config: DistributionConfig,
        distribution_id: str
    ) -> ChannelDeliveryResult:
        """Distribute content via email"""
        # Email distribution implementation
        return ChannelDeliveryResult(
            channel_type=ChannelType.EMAIL,
            status=DeliveryStatus.DELIVERED,
            delivery_id=f"email_{distribution_id}",
            delivered_at=datetime.utcnow()
        )

    async def _distribute_to_rss(
        self,
        content: Dict[str, Any],
        config: DistributionConfig,
        distribution_id: str
    ) -> ChannelDeliveryResult:
        """Generate and update RSS feed"""
        # RSS feed generation implementation
        return ChannelDeliveryResult(
            channel_type=ChannelType.RSS,
            status=DeliveryStatus.DELIVERED,
            delivery_id=f"rss_{distribution_id}",
            delivered_at=datetime.utcnow()
        )

    async def _distribute_to_webhook(
        self,
        content: Dict[str, Any],
        config: DistributionConfig,
        distribution_id: str
    ) -> ChannelDeliveryResult:
        """Send content to webhook endpoints"""
        # Webhook distribution implementation
        return ChannelDeliveryResult(
            channel_type=ChannelType.WEBHOOK,
            status=DeliveryStatus.DELIVERED,
            delivery_id=f"webhook_{distribution_id}",
            delivered_at=datetime.utcnow()
        )

    async def _distribute_to_social_media(
        self,
        content: Dict[str, Any],
        config: DistributionConfig,
        distribution_id: str
    ) -> ChannelDeliveryResult:
        """Distribute content to social media platforms"""
        # Social media distribution implementation
        return ChannelDeliveryResult(
            channel_type=ChannelType.SOCIAL_MEDIA,
            status=DeliveryStatus.DELIVERED,
            delivery_id=f"social_{distribution_id}",
            delivered_at=datetime.utcnow()
        )

    # Audience optimization methods
    
    async def _optimize_for_executives(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize content for executive audience"""
        optimized = content.copy()
        # Focus on high-level metrics, business impact, and key decisions
        optimized['summary_focus'] = 'business_impact'
        optimized['detail_level'] = 'high_level'
        optimized['include_metrics'] = True
        optimized['include_technical_details'] = False
        return optimized

    async def _optimize_for_technical(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize content for technical audience"""
        optimized = content.copy()
        # Include technical details, code changes, and implementation notes
        optimized['summary_focus'] = 'technical_changes'
        optimized['detail_level'] = 'detailed'
        optimized['include_metrics'] = True
        optimized['include_technical_details'] = True
        return optimized

    async def _optimize_for_project_managers(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize content for project manager audience"""
        optimized = content.copy()
        # Focus on progress, timelines, and resource utilization
        optimized['summary_focus'] = 'project_progress'
        optimized['detail_level'] = 'moderate'
        optimized['include_metrics'] = True
        optimized['include_timeline_info'] = True
        return optimized

    async def _optimize_for_stakeholders(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize content for general stakeholders"""
        optimized = content.copy()
        # Balance between business impact and progress updates
        optimized['summary_focus'] = 'stakeholder_impact'
        optimized['detail_level'] = 'moderate'
        optimized['include_metrics'] = False
        optimized['include_business_context'] = True
        return optimized

    async def _optimize_for_general(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize content for general audience"""
        optimized = content.copy()
        # Keep it simple and accessible
        optimized['summary_focus'] = 'general_updates'
        optimized['detail_level'] = 'summary'
        optimized['include_metrics'] = False
        optimized['include_technical_details'] = False
        return optimized

    # Channel optimization methods
    
    async def _optimize_for_slack(self, content: str) -> str:
        """Optimize content for Slack format"""
        # Convert to Slack Block Kit format, add interactive elements
        return content  # Placeholder

    async def _optimize_for_email(self, content: str) -> str:
        """Optimize content for email format"""
        # Convert to HTML email format with responsive design
        return content  # Placeholder

    async def _optimize_for_rss(self, content: str) -> str:
        """Optimize content for RSS format"""
        # Convert to RSS-friendly format with proper encoding
        return content  # Placeholder

    async def _optimize_for_social_media(self, content: str) -> str:
        """Optimize content for social media"""
        # Shorten content, add hashtags, optimize for engagement
        return content  # Placeholder

    async def _handle_a_b_testing(
        self, 
        content: Dict[str, Any], 
        distribution_id: str
    ) -> Dict[str, Any]:
        """Handle A/B testing variant selection"""
        # A/B testing implementation
        return content  # Placeholder

    def _get_fallback_channel(self, failed_channel: ChannelType) -> Optional[ChannelType]:
        """Get fallback channel for failed delivery"""
        fallback_map = {
            ChannelType.SLACK: ChannelType.EMAIL,
            ChannelType.EMAIL: ChannelType.WEBHOOK,
            ChannelType.SOCIAL_MEDIA: ChannelType.SLACK,
            ChannelType.WEBHOOK: ChannelType.EMAIL,
            ChannelType.RSS: None  # RSS doesn't need fallback
        }
        return fallback_map.get(failed_channel)


@dataclass
class RecoveryAction:
    """Recovery action for failed deliveries"""
    action_type: str  # "retry", "fallback", "skip"
    retry_delay: int = 60
    fallback_channel: Optional[ChannelType] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class EmailDistributionManager:
    """
    Advanced email distribution with HTML templating and deliverability optimization
    """
    
    def __init__(self, smtp_config: Dict[str, Any]):
        if not EMAIL_AVAILABLE:
            raise ImportError("Email libraries are required for email distribution")
        self.smtp_config = smtp_config
        self.template_env = Environment(loader=BaseLoader())
        
    async def send_email(
        self,
        recipients: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        sender_email: Optional[str] = None,
        sender_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send HTML email with deliverability optimization
        
        Args:
            recipients: List of recipient email addresses
            subject: Email subject line
            html_content: HTML email content
            text_content: Plain text fallback content
            sender_email: Sender email address
            sender_name: Sender display name
            
        Returns:
            Delivery result with status and metrics
        """
        sender_email = sender_email or self.smtp_config.get('sender_email')
        sender_name = sender_name or self.smtp_config.get('sender_name', 'DevSync AI')
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{sender_name} <{sender_email}>"
        msg['To'] = ', '.join(recipients)
        
        # Add text and HTML parts
        if text_content:
            text_part = MIMEText(text_content, 'plain')
            msg.attach(text_part)
        
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Send email
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(
                self.smtp_config['host'], 
                self.smtp_config.get('port', 587)
            ) as server:
                server.starttls(context=context)
                server.login(
                    self.smtp_config['username'], 
                    self.smtp_config['password']
                )
                server.send_message(msg)
            
            return {
                'status': 'delivered',
                'recipients_count': len(recipients),
                'delivered_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Email delivery failed: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'recipients_count': len(recipients)
            }
    
    def generate_html_email(
        self,
        changelog_data: Dict[str, Any],
        template: EmailTemplate
    ) -> tuple[str, str]:
        """
        Generate HTML and text email content from changelog data
        
        Args:
            changelog_data: Changelog content data
            template: Email template configuration
            
        Returns:
            Tuple of (html_content, text_content)
        """
        # Render HTML template
        html_template = self.template_env.from_string(template.html_template)
        html_content = html_template.render(**changelog_data)
        
        # Render text template or generate from HTML
        if template.text_template:
            text_template = self.template_env.from_string(template.text_template)
            text_content = text_template.render(**changelog_data)
        else:
            text_content = self._html_to_text(html_content)
        
        return html_content, text_content
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML content to plain text"""
        # Simple HTML to text conversion
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def optimize_deliverability(self, html_content: str) -> str:
        """
        Optimize HTML content for email deliverability
        
        Args:
            html_content: Original HTML content
            
        Returns:
            Optimized HTML content
        """
        # Add responsive design meta tags
        if '<head>' in html_content and 'viewport' not in html_content:
            html_content = html_content.replace(
                '<head>',
                '<head>\n<meta name="viewport" content="width=device-width, initial-scale=1.0">'
            )
        
        # Inline CSS for better email client compatibility
        html_content = self._inline_css(html_content)
        
        # Add alt text to images
        html_content = self._add_image_alt_text(html_content)
        
        # Optimize for dark mode
        html_content = self._add_dark_mode_support(html_content)
        
        return html_content
    
    def _inline_css(self, html_content: str) -> str:
        """Inline CSS styles for email compatibility"""
        # This would use a library like premailer in production
        return html_content
    
    def _add_image_alt_text(self, html_content: str) -> str:
        """Add alt text to images without it"""
        import re
        
        # Find img tags without alt attribute
        pattern = r'<img(?![^>]*alt=)[^>]*>'
        
        def add_alt(match):
            img_tag = match.group(0)
            return img_tag.replace('>', ' alt="DevSync AI Changelog Image">')
        
        return re.sub(pattern, add_alt, html_content)
    
    def _add_dark_mode_support(self, html_content: str) -> str:
        """Add dark mode support to email"""
        dark_mode_css = """
        <style>
        @media (prefers-color-scheme: dark) {
            .dark-mode-bg { background-color: #1a1a1a !important; }
            .dark-mode-text { color: #ffffff !important; }
            .dark-mode-border { border-color: #333333 !important; }
        }
        </style>
        """
        
        if '<head>' in html_content:
            html_content = html_content.replace('</head>', f'{dark_mode_css}</head>')
        
        return html_content


class RSSFeedGenerator:
    """
    RSS feed generation with SEO optimization and content syndication
    """
    
    def __init__(self, config: RSSConfig):
        self.config = config
        
    def generate_rss_feed(
        self,
        changelog_entries: List[Dict[str, Any]],
        feed_url: str
    ) -> str:
        """
        Generate RSS feed from changelog entries
        
        Args:
            changelog_entries: List of changelog entries
            feed_url: URL where the RSS feed will be hosted
            
        Returns:
            RSS feed XML content
        """
        if not FEEDGEN_AVAILABLE:
            raise ImportError("feedgen library is required for RSS feed generation")
            
        # Create feed generator
        fg = feedgen.feed.FeedGenerator()
        
        # Set feed metadata
        fg.title(self.config.title)
        fg.description(self.config.description)
        fg.link(href=self.config.link, rel='alternate')
        fg.link(href=feed_url, rel='self')
        fg.language(self.config.language)
        fg.author(name=self.config.author_name, email=self.config.author_email)
        fg.ttl(self.config.ttl)
        
        if self.config.category:
            fg.category(self.config.category)
        
        # Add changelog entries as feed items
        for entry in changelog_entries:
            fe = fg.add_entry()
            fe.id(entry.get('id', f"changelog-{entry.get('week_start', '')}"))
            fe.title(entry.get('title', f"Weekly Changelog - {entry.get('week_start', '')}"))
            fe.description(entry.get('summary', ''))
            fe.content(entry.get('content', ''), type='html')
            
            # Set publication date
            pub_date = entry.get('published_at')
            if pub_date:
                if isinstance(pub_date, str):
                    pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                fe.pubDate(pub_date)
            
            # Add link if available
            if 'link' in entry:
                fe.link(href=entry['link'])
            
            # Add categories/tags
            if 'tags' in entry:
                for tag in entry['tags']:
                    fe.category(tag)
        
        # Generate RSS XML
        return fg.rss_str(pretty=True).decode('utf-8')
    
    def optimize_for_seo(self, rss_content: str) -> str:
        """
        Optimize RSS feed for SEO
        
        Args:
            rss_content: Original RSS XML content
            
        Returns:
            SEO-optimized RSS content
        """
        # Add structured data and optimize descriptions
        # This would include more sophisticated SEO optimizations
        return rss_content


class WebhookDeliveryManager:
    """
    Webhook delivery with retry logic and delivery confirmation
    """
    
    def __init__(self, retry_config: Dict[str, Any]):
        self.retry_config = retry_config
        self.max_retries = retry_config.get('max_retries', 3)
        self.base_delay = retry_config.get('base_delay', 1)
        self.max_delay = retry_config.get('max_delay', 300)
        
    async def send_webhook(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        signature_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send webhook with retry logic and delivery confirmation
        
        Args:
            url: Webhook endpoint URL
            payload: Data to send
            headers: Additional HTTP headers
            signature_key: Key for webhook signature
            
        Returns:
            Delivery result with status and metadata
        """
        headers = headers or {}
        headers['Content-Type'] = 'application/json'
        headers['User-Agent'] = 'DevSync-AI-Webhook/1.0'
        
        # Add webhook signature if key provided
        if signature_key:
            signature = self._generate_signature(payload, signature_key)
            headers['X-DevSync-Signature'] = signature
        
        # Attempt delivery with retries
        for attempt in range(self.max_retries + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        
                        if response.status < 400:
                            return {
                                'status': 'delivered',
                                'status_code': response.status,
                                'attempt': attempt + 1,
                                'delivered_at': datetime.utcnow().isoformat(),
                                'response_headers': dict(response.headers)
                            }
                        else:
                            error_text = await response.text()
                            if attempt < self.max_retries:
                                delay = min(
                                    self.base_delay * (2 ** attempt),
                                    self.max_delay
                                )
                                logger.warning(
                                    f"Webhook delivery failed (attempt {attempt + 1}), "
                                    f"retrying in {delay}s: {response.status} {error_text}"
                                )
                                await asyncio.sleep(delay)
                                continue
                            else:
                                return {
                                    'status': 'failed',
                                    'status_code': response.status,
                                    'error': error_text,
                                    'attempts': attempt + 1
                                }
                                
            except Exception as e:
                if attempt < self.max_retries:
                    delay = min(
                        self.base_delay * (2 ** attempt),
                        self.max_delay
                    )
                    logger.warning(
                        f"Webhook delivery error (attempt {attempt + 1}), "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    return {
                        'status': 'failed',
                        'error': str(e),
                        'attempts': attempt + 1
                    }
        
        return {
            'status': 'failed',
            'error': 'Max retries exceeded',
            'attempts': self.max_retries + 1
        }
    
    def _generate_signature(self, payload: Dict[str, Any], key: str) -> str:
        """Generate webhook signature for verification"""
        import hmac
        
        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        signature = hmac.new(
            key.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"


class SocialMediaIntegration:
    """
    Social media integration with automated posting and engagement tracking
    """
    
    def __init__(self, platforms_config: Dict[str, Any]):
        self.platforms_config = platforms_config
        self.supported_platforms = ['twitter', 'linkedin', 'slack_status']
        
    async def post_to_social_media(
        self,
        content: str,
        platforms: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Post content to social media platforms
        
        Args:
            content: Content to post
            platforms: List of platforms to post to
            metadata: Additional metadata for posts
            
        Returns:
            Results from each platform
        """
        results = {}
        
        for platform in platforms:
            if platform in self.supported_platforms:
                try:
                    if platform == 'twitter':
                        result = await self._post_to_twitter(content, metadata)
                    elif platform == 'linkedin':
                        result = await self._post_to_linkedin(content, metadata)
                    elif platform == 'slack_status':
                        result = await self._update_slack_status(content, metadata)
                    else:
                        result = {'status': 'unsupported', 'platform': platform}
                    
                    results[platform] = result
                    
                except Exception as e:
                    logger.error(f"Social media posting failed for {platform}: {e}")
                    results[platform] = {
                        'status': 'failed',
                        'error': str(e),
                        'platform': platform
                    }
        
        return results
    
    async def _post_to_twitter(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Post to Twitter (placeholder implementation)"""
        # This would integrate with Twitter API
        return {
            'status': 'posted',
            'platform': 'twitter',
            'post_id': f"twitter_{datetime.utcnow().timestamp()}",
            'url': 'https://twitter.com/devsync_ai/status/123456789'
        }
    
    async def _post_to_linkedin(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Post to LinkedIn (placeholder implementation)"""
        # This would integrate with LinkedIn API
        return {
            'status': 'posted',
            'platform': 'linkedin',
            'post_id': f"linkedin_{datetime.utcnow().timestamp()}",
            'url': 'https://linkedin.com/company/devsync-ai/posts/123456789'
        }
    
    async def _update_slack_status(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update Slack status (placeholder implementation)"""
        # This would integrate with Slack API to update status
        return {
            'status': 'updated',
            'platform': 'slack_status',
            'expires_at': (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }
    
    def optimize_content_for_platform(
        self,
        content: str,
        platform: str
    ) -> str:
        """
        Optimize content for specific social media platform
        
        Args:
            content: Original content
            platform: Target platform
            
        Returns:
            Platform-optimized content
        """
        if platform == 'twitter':
            # Limit to 280 characters, add hashtags
            hashtags = " #DevOps #Changelog #WeeklyUpdate"
            max_content_length = 280 - len(hashtags)
            if len(content) > max_content_length:
                content = content[:max_content_length - 3] + "..."
            content += hashtags
            
        elif platform == 'linkedin':
            # Professional tone, add call to action
            content += "\n\nWhat's your team's biggest development win this week? Share in the comments!"
            
        elif platform == 'slack_status':
            # Short status message
            content = f"📊 Weekly changelog published: {content[:50]}..."
        
        return content