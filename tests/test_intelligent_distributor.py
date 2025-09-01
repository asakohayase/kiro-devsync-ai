"""
Tests for IntelligentDistributor - Multi-Channel Distribution and Audience Intelligence

This module tests the intelligent distribution system with mock services,
delivery confirmation validation, and engagement tracking.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

from devsync_ai.core.intelligent_distributor import (
    IntelligentDistributor,
    DistributionConfig,
    ChannelConfig,
    ChannelType,
    AudienceType,
    DeliveryStatus,
    EngagementType,
    DistributionResult,
    ChannelDeliveryResult,
    EngagementMetrics,
    EmailTemplate,
    RSSConfig,
    EmailDistributionManager,
    RSSFeedGenerator,
    WebhookDeliveryManager,
    SocialMediaIntegration,
    RecoveryAction
)


class TestIntelligentDistributor:
    """Test cases for IntelligentDistributor class"""

    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing"""
        return {
            'channels': {
                'slack': {
                    'endpoint': 'https://hooks.slack.com/test',
                    'credentials': {'token': 'test-token'},
                    'template_id': 'slack_default'
                },
                'email': {
                    'endpoint': 'smtp.example.com',
                    'credentials': {
                        'username': 'test@example.com',
                        'password': 'test-password'
                    },
                    'template_id': 'email_default'
                },
                'webhook': {
                    'endpoint': 'https://api.example.com/webhook',
                    'credentials': {'api_key': 'test-key'}
                }
            },
            'templates': {
                'email': {
                    'email_default': {
                        'subject': 'Weekly Changelog - {{ week_start }}',
                        'html': '<h1>{{ title }}</h1><p>{{ content }}</p>',
                        'text': '{{ title }}\n\n{{ content }}'
                    }
                },
                'rss': {
                    'default': {
                        'title': 'DevSync AI Changelog',
                        'description': 'Weekly development updates',
                        'link': 'https://devsync.ai/changelog'
                    }
                }
            }
        }

    @pytest.fixture
    def sample_changelog(self):
        """Sample changelog data for testing"""
        return {
            'title': 'Weekly Changelog - Week 32',
            'week_start': '2024-08-05',
            'week_end': '2024-08-11',
            'summary': 'Major feature releases and bug fixes',
            'content': 'Detailed changelog content here...',
            'metrics': {
                'commits': 45,
                'pull_requests': 12,
                'issues_closed': 8
            },
            'contributors': ['alice', 'bob', 'charlie'],
            'highlights': [
                'New authentication system',
                'Performance improvements',
                'Bug fixes in notification system'
            ]
        }

    @pytest.fixture
    def distributor(self, sample_config):
        """Create IntelligentDistributor instance for testing"""
        return IntelligentDistributor(sample_config)

    def test_initialization(self, distributor, sample_config):
        """Test distributor initialization"""
        assert distributor.config == sample_config
        assert len(distributor.channel_configs) == 3
        assert ChannelType.SLACK in distributor.channel_configs
        assert ChannelType.EMAIL in distributor.channel_configs
        assert ChannelType.WEBHOOK in distributor.channel_configs

    def test_channel_config_loading(self, distributor):
        """Test channel configuration loading"""
        slack_config = distributor.channel_configs[ChannelType.SLACK]
        assert slack_config.channel_type == ChannelType.SLACK
        assert slack_config.endpoint == 'https://hooks.slack.com/test'
        assert slack_config.credentials['token'] == 'test-token'

    def test_template_loading(self, distributor):
        """Test template loading"""
        assert 'email_default' in distributor.email_templates
        email_template = distributor.email_templates['email_default']
        assert email_template.subject_template == 'Weekly Changelog - {{ week_start }}'
        assert '<h1>{{ title }}</h1>' in email_template.html_template

    @pytest.mark.asyncio
    async def test_distribute_changelog_success(self, distributor, sample_changelog):
        """Test successful changelog distribution"""
        config = DistributionConfig(
            channels=[ChannelType.SLACK, ChannelType.EMAIL],
            audience_type=AudienceType.TECHNICAL,
            personalization_enabled=True
        )

        # Mock the distribution methods
        with patch.object(distributor, '_distribute_to_slack', new_callable=AsyncMock) as mock_slack, \
             patch.object(distributor, '_distribute_to_email', new_callable=AsyncMock) as mock_email:
            
            mock_slack.return_value = ChannelDeliveryResult(
                channel_type=ChannelType.SLACK,
                status=DeliveryStatus.DELIVERED,
                delivery_id='slack_123',
                delivered_at=datetime.utcnow()
            )
            
            mock_email.return_value = ChannelDeliveryResult(
                channel_type=ChannelType.EMAIL,
                status=DeliveryStatus.DELIVERED,
                delivery_id='email_123',
                delivered_at=datetime.utcnow()
            )

            result = await distributor.distribute_changelog(sample_changelog, config)

            assert isinstance(result, DistributionResult)
            assert result.total_delivered == 2
            assert result.total_failed == 0
            assert len(result.channel_results) == 2
            assert result.channel_results[ChannelType.SLACK].status == DeliveryStatus.DELIVERED
            assert result.channel_results[ChannelType.EMAIL].status == DeliveryStatus.DELIVERED

    @pytest.mark.asyncio
    async def test_distribute_changelog_partial_failure(self, distributor, sample_changelog):
        """Test changelog distribution with partial failures"""
        config = DistributionConfig(
            channels=[ChannelType.SLACK, ChannelType.EMAIL],
            audience_type=AudienceType.EXECUTIVE
        )

        # Mock one success and one failure
        with patch.object(distributor, '_distribute_to_slack', new_callable=AsyncMock) as mock_slack, \
             patch.object(distributor, '_distribute_to_email', new_callable=AsyncMock) as mock_email:
            
            mock_slack.return_value = ChannelDeliveryResult(
                channel_type=ChannelType.SLACK,
                status=DeliveryStatus.DELIVERED,
                delivery_id='slack_123',
                delivered_at=datetime.utcnow()
            )
            
            mock_email.return_value = ChannelDeliveryResult(
                channel_type=ChannelType.EMAIL,
                status=DeliveryStatus.FAILED,
                error_message='SMTP connection failed'
            )

            result = await distributor.distribute_changelog(sample_changelog, config)

            assert result.total_delivered == 1
            assert result.total_failed == 1
            assert result.channel_results[ChannelType.SLACK].status == DeliveryStatus.DELIVERED
            assert result.channel_results[ChannelType.EMAIL].status == DeliveryStatus.FAILED

    @pytest.mark.asyncio
    async def test_audience_optimization(self, distributor, sample_changelog):
        """Test audience-specific content optimization"""
        # Test executive optimization
        exec_content = await distributor.optimize_content_for_audience(
            sample_changelog, AudienceType.EXECUTIVE
        )
        assert exec_content['summary_focus'] == 'business_impact'
        assert exec_content['detail_level'] == 'high_level'
        assert exec_content['include_metrics'] is True
        assert exec_content['include_technical_details'] is False

        # Test technical optimization
        tech_content = await distributor.optimize_content_for_audience(
            sample_changelog, AudienceType.TECHNICAL
        )
        assert tech_content['summary_focus'] == 'technical_changes'
        assert tech_content['detail_level'] == 'detailed'
        assert tech_content['include_technical_details'] is True

        # Test project manager optimization
        pm_content = await distributor.optimize_content_for_audience(
            sample_changelog, AudienceType.PROJECT_MANAGER
        )
        assert pm_content['summary_focus'] == 'project_progress'
        assert pm_content['include_timeline_info'] is True

    @pytest.mark.asyncio
    async def test_channel_optimization(self, distributor):
        """Test channel-specific content optimization"""
        content = "Test changelog content"
        
        slack_content = await distributor.optimize_content_for_channel(
            content, ChannelType.SLACK
        )
        assert isinstance(slack_content, str)
        
        email_content = await distributor.optimize_content_for_channel(
            content, ChannelType.EMAIL
        )
        assert isinstance(email_content, str)

    @pytest.mark.asyncio
    async def test_engagement_tracking(self, distributor):
        """Test engagement metrics tracking"""
        distribution_id = "test_dist_123"
        
        metrics = await distributor.track_engagement_metrics(distribution_id)
        
        assert isinstance(metrics, EngagementMetrics)
        assert metrics.distribution_id == distribution_id
        assert isinstance(metrics.channel_type, ChannelType)
        assert isinstance(metrics.engagement_type, EngagementType)

    @pytest.mark.asyncio
    async def test_delivery_confirmation(self, distributor):
        """Test delivery confirmation management"""
        distribution_id = "test_dist_123"
        
        # Test pending status
        status = await distributor.manage_delivery_confirmation(distribution_id)
        assert status == DeliveryStatus.PENDING
        
        # Test with stored confirmation
        distributor.delivery_confirmations[distribution_id] = ChannelDeliveryResult(
            channel_type=ChannelType.SLACK,
            status=DeliveryStatus.DELIVERED
        )
        
        status = await distributor.manage_delivery_confirmation(distribution_id)
        assert status == DeliveryStatus.DELIVERED

    @pytest.mark.asyncio
    async def test_failure_recovery(self, distributor):
        """Test delivery failure recovery mechanisms"""
        failed_delivery = ChannelDeliveryResult(
            channel_type=ChannelType.SLACK,
            status=DeliveryStatus.FAILED,
            retry_count=1,
            error_message="Connection timeout"
        )
        
        recovery_action = await distributor.handle_delivery_failures(failed_delivery)
        
        assert isinstance(recovery_action, RecoveryAction)
        assert recovery_action.action_type == "retry"
        assert recovery_action.retry_delay > 0

        # Test max retries exceeded
        failed_delivery.retry_count = 5
        recovery_action = await distributor.handle_delivery_failures(failed_delivery)
        assert recovery_action.action_type == "fallback"
        assert recovery_action.fallback_channel is not None

    def test_distribution_id_generation(self, distributor, sample_changelog):
        """Test unique distribution ID generation"""
        dist_id_1 = distributor._generate_distribution_id(sample_changelog)
        dist_id_2 = distributor._generate_distribution_id(sample_changelog)
        
        # Same content should generate same ID (within same second)
        assert dist_id_1 == dist_id_2
        
        # Different content should generate different ID
        modified_changelog = sample_changelog.copy()
        modified_changelog['title'] = 'Different Title'
        dist_id_3 = distributor._generate_distribution_id(modified_changelog)
        assert dist_id_1 != dist_id_3

    def test_fallback_channel_mapping(self, distributor):
        """Test fallback channel selection"""
        assert distributor._get_fallback_channel(ChannelType.SLACK) == ChannelType.EMAIL
        assert distributor._get_fallback_channel(ChannelType.EMAIL) == ChannelType.WEBHOOK
        assert distributor._get_fallback_channel(ChannelType.RSS) is None


class TestEmailDistributionManager:
    """Test cases for EmailDistributionManager"""

    @pytest.fixture
    def smtp_config(self):
        """Sample SMTP configuration"""
        return {
            'host': 'smtp.example.com',
            'port': 587,
            'username': 'test@example.com',
            'password': 'test-password',
            'sender_email': 'noreply@devsync.ai',
            'sender_name': 'DevSync AI'
        }

    @pytest.fixture
    def email_manager(self, smtp_config):
        """Create EmailDistributionManager instance"""
        return EmailDistributionManager(smtp_config)

    @pytest.fixture
    def email_template(self):
        """Sample email template"""
        return EmailTemplate(
            subject_template='Weekly Update - {{ week_start }}',
            html_template='<h1>{{ title }}</h1><div>{{ content }}</div>',
            text_template='{{ title }}\n\n{{ content }}',
            sender_name='DevSync AI',
            sender_email='noreply@devsync.ai'
        )

    @pytest.mark.asyncio
    async def test_send_email_success(self, email_manager):
        """Test successful email sending"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = await email_manager.send_email(
                recipients=['test@example.com'],
                subject='Test Subject',
                html_content='<p>Test content</p>',
                text_content='Test content'
            )
            
            assert result['status'] == 'delivered'
            assert result['recipients_count'] == 1
            assert 'delivered_at' in result
            mock_server.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_failure(self, email_manager):
        """Test email sending failure"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = Exception("SMTP connection failed")
            
            result = await email_manager.send_email(
                recipients=['test@example.com'],
                subject='Test Subject',
                html_content='<p>Test content</p>'
            )
            
            assert result['status'] == 'failed'
            assert 'error' in result
            assert result['recipients_count'] == 1

    def test_generate_html_email(self, email_manager, email_template):
        """Test HTML email generation from template"""
        changelog_data = {
            'title': 'Weekly Changelog',
            'week_start': '2024-08-05',
            'content': 'Changelog content here'
        }
        
        html_content, text_content = email_manager.generate_html_email(
            changelog_data, email_template
        )
        
        assert '<h1>Weekly Changelog</h1>' in html_content
        assert 'Changelog content here' in html_content
        assert 'Weekly Changelog' in text_content
        assert 'Changelog content here' in text_content

    def test_html_to_text_conversion(self, email_manager):
        """Test HTML to text conversion"""
        html_content = '<h1>Title</h1><p>Paragraph content</p><br><strong>Bold text</strong>'
        text_content = email_manager._html_to_text(html_content)
        
        assert 'Title' in text_content
        assert 'Paragraph content' in text_content
        assert 'Bold text' in text_content
        assert '<h1>' not in text_content
        assert '<p>' not in text_content

    def test_deliverability_optimization(self, email_manager):
        """Test email deliverability optimization"""
        html_content = '<html><head></head><body><img src="test.jpg"><p>Content</p></body></html>'
        optimized = email_manager.optimize_deliverability(html_content)
        
        assert 'viewport' in optimized
        assert 'alt=' in optimized
        assert 'prefers-color-scheme: dark' in optimized

    def test_add_image_alt_text(self, email_manager):
        """Test automatic alt text addition to images"""
        html_content = '<img src="test.jpg"><img src="test2.jpg" alt="existing">'
        result = email_manager._add_image_alt_text(html_content)
        
        # Should add alt text to first image but not second
        assert result.count('alt=') == 2
        assert 'alt="existing"' in result
        assert 'alt="DevSync AI Changelog Image"' in result


class TestRSSFeedGenerator:
    """Test cases for RSSFeedGenerator"""

    @pytest.fixture
    def rss_config(self):
        """Sample RSS configuration"""
        return RSSConfig(
            title='DevSync AI Changelog',
            description='Weekly development updates',
            link='https://devsync.ai/changelog',
            author_name='DevSync AI',
            author_email='noreply@devsync.ai'
        )

    @pytest.fixture
    def rss_generator(self, rss_config):
        """Create RSSFeedGenerator instance"""
        return RSSFeedGenerator(rss_config)

    @pytest.fixture
    def changelog_entries(self):
        """Sample changelog entries for RSS"""
        return [
            {
                'id': 'changelog-2024-08-05',
                'title': 'Weekly Changelog - Week 32',
                'summary': 'Major feature releases',
                'content': '<p>Detailed changelog content</p>',
                'published_at': '2024-08-05T10:00:00Z',
                'link': 'https://devsync.ai/changelog/2024-08-05',
                'tags': ['features', 'releases']
            },
            {
                'id': 'changelog-2024-07-29',
                'title': 'Weekly Changelog - Week 31',
                'summary': 'Bug fixes and improvements',
                'content': '<p>Bug fix details</p>',
                'published_at': '2024-07-29T10:00:00Z',
                'link': 'https://devsync.ai/changelog/2024-07-29',
                'tags': ['bugfixes', 'improvements']
            }
        ]

    def test_generate_rss_feed(self, rss_generator, changelog_entries):
        """Test RSS feed generation"""
        feed_url = 'https://devsync.ai/rss'
        rss_content = rss_generator.generate_rss_feed(changelog_entries, feed_url)
        
        assert isinstance(rss_content, str)
        assert '<?xml version=' in rss_content
        assert '<rss version="2.0"' in rss_content
        assert 'DevSync AI Changelog' in rss_content
        assert 'Weekly development updates' in rss_content
        assert 'Weekly Changelog - Week 32' in rss_content
        assert 'Weekly Changelog - Week 31' in rss_content

    def test_rss_feed_metadata(self, rss_generator, changelog_entries):
        """Test RSS feed metadata inclusion"""
        feed_url = 'https://devsync.ai/rss'
        rss_content = rss_generator.generate_rss_feed(changelog_entries, feed_url)
        
        assert 'https://devsync.ai/changelog' in rss_content
        assert 'noreply@devsync.ai' in rss_content
        assert '<language>en-US</language>' in rss_content
        assert '<ttl>60</ttl>' in rss_content

    def test_rss_feed_items(self, rss_generator, changelog_entries):
        """Test RSS feed item generation"""
        feed_url = 'https://devsync.ai/rss'
        rss_content = rss_generator.generate_rss_feed(changelog_entries, feed_url)
        
        # Check for item content
        assert 'changelog-2024-08-05' in rss_content
        assert 'Major feature releases' in rss_content
        assert 'Detailed changelog content' in rss_content
        assert 'https://devsync.ai/changelog/2024-08-05' in rss_content

    def test_seo_optimization(self, rss_generator):
        """Test RSS feed SEO optimization"""
        rss_content = '<rss><channel><title>Test</title></channel></rss>'
        optimized = rss_generator.optimize_for_seo(rss_content)
        
        # Basic test - in production this would include more optimizations
        assert isinstance(optimized, str)
        assert len(optimized) >= len(rss_content)


class TestWebhookDeliveryManager:
    """Test cases for WebhookDeliveryManager"""

    @pytest.fixture
    def retry_config(self):
        """Sample retry configuration"""
        return {
            'max_retries': 3,
            'base_delay': 1,
            'max_delay': 60
        }

    @pytest.fixture
    def webhook_manager(self, retry_config):
        """Create WebhookDeliveryManager instance"""
        return WebhookDeliveryManager(retry_config)

    @pytest.fixture
    def sample_payload(self):
        """Sample webhook payload"""
        return {
            'event': 'changelog.published',
            'data': {
                'title': 'Weekly Changelog',
                'week': '2024-08-05',
                'url': 'https://devsync.ai/changelog/2024-08-05'
            },
            'timestamp': '2024-08-05T10:00:00Z'
        }

    def test_webhook_manager_initialization(self, webhook_manager):
        """Test webhook manager initialization"""
        assert webhook_manager.max_retries == 3
        assert webhook_manager.base_delay == 1
        assert webhook_manager.max_delay == 60

    def test_generate_signature(self, webhook_manager, sample_payload):
        """Test webhook signature generation"""
        signature = webhook_manager._generate_signature(sample_payload, 'test-key')
        
        assert signature.startswith('sha256=')
        assert len(signature) == 71  # 'sha256=' + 64 hex chars
        
        # Same payload and key should generate same signature
        signature2 = webhook_manager._generate_signature(sample_payload, 'test-key')
        assert signature == signature2
        
        # Different key should generate different signature
        signature3 = webhook_manager._generate_signature(sample_payload, 'different-key')
        assert signature != signature3


class TestSocialMediaIntegration:
    """Test cases for SocialMediaIntegration"""

    @pytest.fixture
    def platforms_config(self):
        """Sample social media platforms configuration"""
        return {
            'twitter': {
                'api_key': 'test-twitter-key',
                'api_secret': 'test-twitter-secret',
                'access_token': 'test-access-token'
            },
            'linkedin': {
                'client_id': 'test-linkedin-id',
                'client_secret': 'test-linkedin-secret'
            }
        }

    @pytest.fixture
    def social_media(self, platforms_config):
        """Create SocialMediaIntegration instance"""
        return SocialMediaIntegration(platforms_config)

    @pytest.mark.asyncio
    async def test_post_to_social_media_success(self, social_media):
        """Test successful social media posting"""
        content = "Weekly changelog published! Check out our latest updates."
        platforms = ['twitter', 'linkedin']
        
        with patch.object(social_media, '_post_to_twitter', new_callable=AsyncMock) as mock_twitter, \
             patch.object(social_media, '_post_to_linkedin', new_callable=AsyncMock) as mock_linkedin:
            
            mock_twitter.return_value = {
                'status': 'posted',
                'platform': 'twitter',
                'post_id': 'twitter_123',
                'url': 'https://twitter.com/devsync_ai/status/123'
            }
            
            mock_linkedin.return_value = {
                'status': 'posted',
                'platform': 'linkedin',
                'post_id': 'linkedin_123',
                'url': 'https://linkedin.com/company/devsync-ai/posts/123'
            }
            
            results = await social_media.post_to_social_media(content, platforms)
            
            assert len(results) == 2
            assert results['twitter']['status'] == 'posted'
            assert results['linkedin']['status'] == 'posted'
            mock_twitter.assert_called_once_with(content, None)
            mock_linkedin.assert_called_once_with(content, None)

    @pytest.mark.asyncio
    async def test_post_to_social_media_partial_failure(self, social_media):
        """Test social media posting with partial failures"""
        content = "Test content"
        platforms = ['twitter', 'linkedin']
        
        with patch.object(social_media, '_post_to_twitter', new_callable=AsyncMock) as mock_twitter, \
             patch.object(social_media, '_post_to_linkedin', new_callable=AsyncMock) as mock_linkedin:
            
            mock_twitter.return_value = {
                'status': 'posted',
                'platform': 'twitter',
                'post_id': 'twitter_123'
            }
            
            mock_linkedin.side_effect = Exception("LinkedIn API error")
            
            results = await social_media.post_to_social_media(content, platforms)
            
            assert results['twitter']['status'] == 'posted'
            assert results['linkedin']['status'] == 'failed'
            assert 'error' in results['linkedin']

    def test_optimize_content_for_twitter(self, social_media):
        """Test content optimization for Twitter"""
        long_content = "This is a very long content that exceeds Twitter's character limit. " * 10
        optimized = social_media.optimize_content_for_platform(long_content, 'twitter')
        
        assert len(optimized) <= 280
        assert '...' in optimized  # Should contain ellipsis for truncated content
        assert '#DevOps' in optimized
        assert '#Changelog' in optimized
        assert optimized.endswith('#WeeklyUpdate')

    def test_optimize_content_for_linkedin(self, social_media):
        """Test content optimization for LinkedIn"""
        content = "Weekly changelog published!"
        optimized = social_media.optimize_content_for_platform(content, 'linkedin')
        
        assert content in optimized
        assert "What's your team's biggest development win" in optimized
        assert "Share in the comments!" in optimized

    def test_optimize_content_for_slack_status(self, social_media):
        """Test content optimization for Slack status"""
        content = "This is a long changelog description with many details about the weekly updates"
        optimized = social_media.optimize_content_for_platform(content, 'slack_status')
        
        assert optimized.startswith('📊 Weekly changelog published:')
        assert len(optimized) <= 100  # Reasonable status length
        assert '...' in optimized

    @pytest.mark.asyncio
    async def test_unsupported_platform(self, social_media):
        """Test handling of unsupported platforms"""
        content = "Test content"
        platforms = ['unsupported_platform']
        
        results = await social_media.post_to_social_media(content, platforms)
        
        assert len(results) == 0  # Unsupported platforms are filtered out


class TestIntegrationScenarios:
    """Integration test scenarios for the complete distribution system"""

    @pytest.fixture
    def full_config(self):
        """Complete configuration for integration testing"""
        return {
            'channels': {
                'slack': {
                    'endpoint': 'https://hooks.slack.com/test',
                    'credentials': {'token': 'test-token'}
                },
                'email': {
                    'endpoint': 'smtp.example.com',
                    'credentials': {
                        'username': 'test@example.com',
                        'password': 'test-password'
                    }
                },
                'webhook': {
                    'endpoint': 'https://api.example.com/webhook',
                    'credentials': {'api_key': 'test-key'}
                },
                'rss': {
                    'endpoint': 'https://devsync.ai/rss'
                }
            },
            'templates': {
                'email': {
                    'default': {
                        'subject': 'Weekly Changelog - {{ week_start }}',
                        'html': '<h1>{{ title }}</h1><p>{{ summary }}</p>',
                        'text': '{{ title }}\n\n{{ summary }}'
                    }
                },
                'rss': {
                    'default': {
                        'title': 'DevSync AI Changelog',
                        'description': 'Weekly updates',
                        'link': 'https://devsync.ai'
                    }
                }
            }
        }

    @pytest.fixture
    def comprehensive_changelog(self):
        """Comprehensive changelog for integration testing"""
        return {
            'title': 'Weekly Changelog - Week 32, 2024',
            'week_start': '2024-08-05',
            'week_end': '2024-08-11',
            'summary': 'Major feature releases, performance improvements, and critical bug fixes',
            'content': '''
            <h2>🚀 New Features</h2>
            <ul>
                <li>Advanced user authentication system</li>
                <li>Real-time collaboration features</li>
                <li>Enhanced dashboard analytics</li>
            </ul>
            
            <h2>🐛 Bug Fixes</h2>
            <ul>
                <li>Fixed notification delivery issues</li>
                <li>Resolved memory leaks in data processing</li>
                <li>Corrected timezone handling in reports</li>
            </ul>
            
            <h2>⚡ Performance Improvements</h2>
            <ul>
                <li>50% faster query processing</li>
                <li>Reduced memory usage by 30%</li>
                <li>Optimized API response times</li>
            </ul>
            ''',
            'metrics': {
                'commits': 67,
                'pull_requests': 18,
                'issues_closed': 12,
                'contributors': 8,
                'lines_added': 2450,
                'lines_removed': 890
            },
            'contributors': [
                {'name': 'Alice Johnson', 'commits': 23, 'role': 'Senior Developer'},
                {'name': 'Bob Smith', 'commits': 18, 'role': 'DevOps Engineer'},
                {'name': 'Charlie Brown', 'commits': 15, 'role': 'Frontend Developer'},
                {'name': 'Diana Prince', 'commits': 11, 'role': 'QA Engineer'}
            ],
            'highlights': [
                'Authentication system overhaul completed',
                'Performance benchmarks exceeded targets',
                'Zero critical bugs in production',
                'Team velocity increased by 25%'
            ],
            'breaking_changes': [
                'API endpoint /v1/users deprecated, use /v2/users',
                'Configuration format updated for better security'
            ],
            'upcoming': [
                'Mobile app beta release',
                'Advanced reporting features',
                'Third-party integrations expansion'
            ]
        }

    @pytest.mark.asyncio
    async def test_end_to_end_distribution(self, full_config, comprehensive_changelog):
        """Test complete end-to-end distribution workflow"""
        distributor = IntelligentDistributor(full_config)
        
        config = DistributionConfig(
            channels=[ChannelType.SLACK, ChannelType.EMAIL, ChannelType.WEBHOOK],
            audience_type=AudienceType.TECHNICAL,
            personalization_enabled=True,
            a_b_testing_enabled=False,
            retry_attempts=2,
            delivery_confirmation=True,
            engagement_tracking=True
        )
        
        # Mock all distribution methods
        with patch.object(distributor, '_distribute_to_slack', new_callable=AsyncMock) as mock_slack, \
             patch.object(distributor, '_distribute_to_email', new_callable=AsyncMock) as mock_email, \
             patch.object(distributor, '_distribute_to_webhook', new_callable=AsyncMock) as mock_webhook:
            
            # Configure successful responses
            mock_slack.return_value = ChannelDeliveryResult(
                channel_type=ChannelType.SLACK,
                status=DeliveryStatus.DELIVERED,
                delivery_id='slack_e2e_123',
                delivered_at=datetime.utcnow(),
                engagement_metrics={'views': 45, 'reactions': 12}
            )
            
            mock_email.return_value = ChannelDeliveryResult(
                channel_type=ChannelType.EMAIL,
                status=DeliveryStatus.DELIVERED,
                delivery_id='email_e2e_123',
                delivered_at=datetime.utcnow(),
                engagement_metrics={'opens': 78, 'clicks': 23}
            )
            
            mock_webhook.return_value = ChannelDeliveryResult(
                channel_type=ChannelType.WEBHOOK,
                status=DeliveryStatus.DELIVERED,
                delivery_id='webhook_e2e_123',
                delivered_at=datetime.utcnow()
            )
            
            # Execute distribution
            result = await distributor.distribute_changelog(comprehensive_changelog, config)
            
            # Verify results
            assert isinstance(result, DistributionResult)
            assert result.total_delivered == 3
            assert result.total_failed == 0
            assert len(result.channel_results) == 3
            
            # Verify all channels were called
            mock_slack.assert_called_once()
            mock_email.assert_called_once()
            mock_webhook.assert_called_once()
            
            # Verify engagement metrics were captured
            slack_result = result.channel_results[ChannelType.SLACK]
            assert slack_result.engagement_metrics['views'] == 45
            assert slack_result.engagement_metrics['reactions'] == 12
            
            email_result = result.channel_results[ChannelType.EMAIL]
            assert email_result.engagement_metrics['opens'] == 78
            assert email_result.engagement_metrics['clicks'] == 23

    @pytest.mark.asyncio
    async def test_multi_audience_distribution(self, full_config, comprehensive_changelog):
        """Test distribution to multiple audience types"""
        distributor = IntelligentDistributor(full_config)
        
        audiences = [
            AudienceType.EXECUTIVE,
            AudienceType.TECHNICAL,
            AudienceType.PROJECT_MANAGER
        ]
        
        results = []
        
        for audience in audiences:
            config = DistributionConfig(
                channels=[ChannelType.SLACK],
                audience_type=audience,
                personalization_enabled=True
            )
            
            with patch.object(distributor, '_distribute_to_slack', new_callable=AsyncMock) as mock_slack:
                mock_slack.return_value = ChannelDeliveryResult(
                    channel_type=ChannelType.SLACK,
                    status=DeliveryStatus.DELIVERED,
                    delivery_id=f'slack_{audience.value}_123',
                    delivered_at=datetime.utcnow()
                )
                
                result = await distributor.distribute_changelog(comprehensive_changelog, config)
                results.append((audience, result))
        
        # Verify all audiences were processed
        assert len(results) == 3
        for audience, result in results:
            assert result.total_delivered == 1
            assert result.total_failed == 0

    @pytest.mark.asyncio
    async def test_failure_recovery_workflow(self, full_config, comprehensive_changelog):
        """Test complete failure recovery workflow"""
        distributor = IntelligentDistributor(full_config)
        
        config = DistributionConfig(
            channels=[ChannelType.SLACK, ChannelType.EMAIL],
            audience_type=AudienceType.GENERAL,
            retry_attempts=3
        )
        
        with patch.object(distributor, '_distribute_to_slack', new_callable=AsyncMock) as mock_slack, \
             patch.object(distributor, '_distribute_to_email', new_callable=AsyncMock) as mock_email:
            
            # Slack fails, email succeeds
            mock_slack.return_value = ChannelDeliveryResult(
                channel_type=ChannelType.SLACK,
                status=DeliveryStatus.FAILED,
                error_message='Slack API rate limit exceeded',
                retry_count=3
            )
            
            mock_email.return_value = ChannelDeliveryResult(
                channel_type=ChannelType.EMAIL,
                status=DeliveryStatus.DELIVERED,
                delivery_id='email_recovery_123',
                delivered_at=datetime.utcnow()
            )
            
            result = await distributor.distribute_changelog(comprehensive_changelog, config)
            
            assert result.total_delivered == 1
            assert result.total_failed == 1
            
            # Test recovery action for failed delivery
            failed_delivery = result.channel_results[ChannelType.SLACK]
            recovery_action = await distributor.handle_delivery_failures(failed_delivery)
            
            assert recovery_action.action_type == "fallback"
            assert recovery_action.fallback_channel == ChannelType.EMAIL


if __name__ == '__main__':
    pytest.main([__file__, '-v'])