"""Tests for MessageTemplateFactory."""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from devsync_ai.core.template_factory import (
    MessageTemplateFactory, TemplateType, TemplateRegistration, 
    CacheEntry, FactoryConfig
)
from devsync_ai.core.base_template import SlackMessageTemplate
from devsync_ai.core.message_formatter import TemplateConfig, SlackMessage
from devsync_ai.core.exceptions import TemplateError


class MockTemplate(SlackMessageTemplate):
    """Mock template for testing."""
    
    REQUIRED_FIELDS = ['title']
    
    def _create_message_blocks(self, data):
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Mock template: {data.get('title', 'No title')}"
                }
            }
        ]


class SlowMockTemplate(SlackMessageTemplate):
    """Mock template that takes time to create (for performance testing)."""
    
    REQUIRED_FIELDS = ['title']
    
    def __init__(self, *args, **kwargs):
        time.sleep(0.2)  # Simulate slow initialization
        super().__init__(*args, **kwargs)
    
    def _create_message_blocks(self, data):
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Slow template: {data.get('title', 'No title')}"
                }
            }
        ]


class TestMessageTemplateFactory:
    """Test MessageTemplateFactory functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = FactoryConfig(
            cache_ttl_seconds=60,
            max_cache_size=10,
            enable_metrics=True,
            performance_threshold_ms=50.0
        )
        self.factory = MessageTemplateFactory(self.config)
    
    def test_factory_initialization(self):
        """Test factory initialization."""
        assert self.factory.config == self.config
        assert len(self.factory._registry) == 0
        assert len(self.factory._cache) == 0
        assert len(self.factory._metrics) == 0
    
    def test_template_registration(self):
        """Test template registration."""
        # Register template
        self.factory.register_template(
            name="test_template",
            template_class=MockTemplate,
            template_type=TemplateType.STANDUP,
            version="1.0.0",
            description="Test template"
        )
        
        # Check registration
        assert "test_template" in self.factory._registry
        assert TemplateType.STANDUP in self.factory._type_mapping
        
        registration = self.factory._registry["test_template"]
        assert registration.template_class == MockTemplate
        assert registration.template_type == TemplateType.STANDUP
        assert registration.version == "1.0.0"
        assert registration.description == "Test template"
        assert registration.usage_count == 0
    
    def test_template_registration_invalid_class(self):
        """Test registration with invalid template class."""
        class InvalidTemplate:
            pass
        
        with pytest.raises(TemplateError, match="must inherit from SlackMessageTemplate"):
            self.factory.register_template(
                name="invalid",
                template_class=InvalidTemplate,
                template_type=TemplateType.STANDUP
            )
    
    def test_template_registration_override_warning(self, caplog):
        """Test warning when overriding existing registration."""
        # Register first template
        self.factory.register_template(
            name="test_template",
            template_class=MockTemplate,
            template_type=TemplateType.STANDUP
        )
        
        # Register with same name (should warn)
        self.factory.register_template(
            name="test_template",
            template_class=MockTemplate,
            template_type=TemplateType.PR_NEW
        )
        
        assert "Overriding existing template registration" in caplog.text
    
    def test_create_template_by_type(self):
        """Test creating template by type."""
        # Register template
        self.factory.register_template(
            name="test_template",
            template_class=MockTemplate,
            template_type=TemplateType.STANDUP
        )
        
        # Create template
        template = self.factory.create_template(TemplateType.STANDUP)
        
        assert isinstance(template, MockTemplate)
        assert self.factory._registry["test_template"].usage_count == 1
        assert self.factory._registry["test_template"].last_used is not None
    
    def test_create_template_by_string(self):
        """Test creating template by string type."""
        # Register template
        self.factory.register_template(
            name="test_template",
            template_class=MockTemplate,
            template_type=TemplateType.STANDUP
        )
        
        # Create template by string
        template = self.factory.create_template("standup")
        
        assert isinstance(template, MockTemplate)
    
    def test_create_template_by_name(self):
        """Test creating template by registered name."""
        # Register template
        self.factory.register_template(
            name="test_template",
            template_class=MockTemplate,
            template_type=TemplateType.STANDUP
        )
        
        # Create template by name
        template = self.factory.create_template("test_template")
        
        assert isinstance(template, MockTemplate)
    
    def test_create_template_unknown_type(self):
        """Test creating template with unknown type."""
        with pytest.raises(TemplateError, match="Unknown template type"):
            self.factory.create_template("unknown_type")
        
        with pytest.raises(TemplateError, match="Template type .* not registered"):
            self.factory.create_template(TemplateType.STANDUP)
    
    def test_template_caching(self):
        """Test template instance caching."""
        # Register template
        self.factory.register_template(
            name="test_template",
            template_class=MockTemplate,
            template_type=TemplateType.STANDUP
        )
        
        # Create first template (should cache)
        template1 = self.factory.create_template(TemplateType.STANDUP, use_cache=True)
        
        # Create second template (should use cache)
        template2 = self.factory.create_template(TemplateType.STANDUP, use_cache=True)
        
        # Should be the same instance from cache
        assert template1 is template2
        assert len(self.factory._cache) == 1
    
    def test_template_caching_disabled(self):
        """Test template creation without caching."""
        # Register template
        self.factory.register_template(
            name="test_template",
            template_class=MockTemplate,
            template_type=TemplateType.STANDUP
        )
        
        # Create templates without caching
        template1 = self.factory.create_template(TemplateType.STANDUP, use_cache=False)
        template2 = self.factory.create_template(TemplateType.STANDUP, use_cache=False)
        
        # Should be different instances
        assert template1 is not template2
        assert len(self.factory._cache) == 0
    
    def test_template_caching_different_configs(self):
        """Test caching with different configurations."""
        # Register template
        self.factory.register_template(
            name="test_template",
            template_class=MockTemplate,
            template_type=TemplateType.STANDUP
        )
        
        config1 = TemplateConfig(team_id="team1")
        config2 = TemplateConfig(team_id="team2")
        
        # Create templates with different configs
        template1 = self.factory.create_template(TemplateType.STANDUP, config=config1)
        template2 = self.factory.create_template(TemplateType.STANDUP, config=config2)
        
        # Should be different instances (different cache keys)
        assert template1 is not template2
        assert len(self.factory._cache) == 2
    
    def test_cache_expiration(self):
        """Test cache entry expiration."""
        # Set short TTL for testing
        self.factory.config.cache_ttl_seconds = 1
        
        # Register template
        self.factory.register_template(
            name="test_template",
            template_class=MockTemplate,
            template_type=TemplateType.STANDUP
        )
        
        # Create template (should cache)
        template1 = self.factory.create_template(TemplateType.STANDUP)
        assert len(self.factory._cache) == 1
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Create template again (should create new instance)
        template2 = self.factory.create_template(TemplateType.STANDUP)
        
        # Should be different instances
        assert template1 is not template2
        # Cache should still have 1 entry (old one removed, new one added)
        assert len(self.factory._cache) == 1
    
    def test_cache_size_limit(self):
        """Test cache size limit enforcement."""
        # Set small cache size
        self.factory.config.max_cache_size = 2
        
        # Register templates
        for i in range(3):
            self.factory.register_template(
                name=f"template_{i}",
                template_class=MockTemplate,
                template_type=list(TemplateType)[i]
            )
        
        # Create templates (should trigger eviction)
        for i in range(3):
            self.factory.create_template(list(TemplateType)[i])
        
        # Cache should not exceed max size
        assert len(self.factory._cache) <= self.factory.config.max_cache_size
    
    def test_performance_metrics(self):
        """Test performance metrics collection."""
        # Register slow template
        self.factory.register_template(
            name="slow_template",
            template_class=SlowMockTemplate,
            template_type=TemplateType.STANDUP
        )
        
        # Create template (should record metrics)
        self.factory.create_template(TemplateType.STANDUP, use_cache=False)
        
        # Check metrics
        metrics = self.factory.get_template_metrics("standup")
        assert "creation_times" in metrics
        assert "usage_count" in metrics
        assert "average_creation_time" in metrics
        assert metrics["usage_count"] == 1
        assert metrics["average_creation_time"] > 0
    
    def test_performance_warning(self, caplog):
        """Test performance warning for slow templates."""
        # Set low threshold
        self.factory.config.performance_threshold_ms = 10.0
        
        # Register slow template
        self.factory.register_template(
            name="slow_template",
            template_class=SlowMockTemplate,
            template_type=TemplateType.STANDUP
        )
        
        # Create template (should trigger warning)
        self.factory.create_template(TemplateType.STANDUP, use_cache=False)
        
        assert "Template creation took" in caplog.text
        assert "threshold:" in caplog.text
    
    def test_get_template_by_event_type(self):
        """Test getting template by event type."""
        # Register template
        self.factory.register_template(
            name="standup_template",
            template_class=MockTemplate,
            template_type=TemplateType.STANDUP
        )
        
        # Get template by event type
        template = self.factory.get_template_by_event_type(
            event_type="standup.daily",
            event_data={"team": "engineering"}
        )
        
        assert isinstance(template, MockTemplate)
    
    def test_get_template_by_event_type_unknown(self):
        """Test getting template by unknown event type."""
        with pytest.raises(TemplateError, match="No template mapping found"):
            self.factory.get_template_by_event_type(
                event_type="unknown.event",
                event_data={}
            )
    
    def test_get_registered_templates(self):
        """Test getting registered templates."""
        # Register templates
        self.factory.register_template(
            name="template1",
            template_class=MockTemplate,
            template_type=TemplateType.STANDUP
        )
        self.factory.register_template(
            name="template2",
            template_class=MockTemplate,
            template_type=TemplateType.PR_NEW
        )
        
        # Get registered templates
        templates = self.factory.get_registered_templates()
        
        assert len(templates) == 2
        assert "template1" in templates
        assert "template2" in templates
        assert isinstance(templates["template1"], TemplateRegistration)
    
    def test_clear_cache(self):
        """Test cache clearing."""
        # Register templates
        self.factory.register_template(
            name="template1",
            template_class=MockTemplate,
            template_type=TemplateType.STANDUP
        )
        self.factory.register_template(
            name="template2",
            template_class=MockTemplate,
            template_type=TemplateType.PR_NEW
        )
        
        # Create templates to populate cache
        self.factory.create_template(TemplateType.STANDUP)
        self.factory.create_template(TemplateType.PR_NEW)
        
        assert len(self.factory._cache) == 2
        
        # Clear specific template type
        cleared = self.factory.clear_cache(TemplateType.STANDUP)
        assert cleared == 1
        assert len(self.factory._cache) == 1
        
        # Clear all cache
        cleared = self.factory.clear_cache()
        assert cleared == 1
        assert len(self.factory._cache) == 0
    
    def test_get_cache_stats(self):
        """Test cache statistics."""
        # Register template
        self.factory.register_template(
            name="test_template",
            template_class=MockTemplate,
            template_type=TemplateType.STANDUP
        )
        
        # Create template to populate cache
        self.factory.create_template(TemplateType.STANDUP)
        
        # Get cache stats
        stats = self.factory.get_cache_stats()
        
        assert "total_entries" in stats
        assert "expired_entries" in stats
        assert "active_entries" in stats
        assert "total_access_count" in stats
        assert "cache_hit_rate" in stats
        assert "max_cache_size" in stats
        assert "cache_utilization" in stats
        
        assert stats["total_entries"] == 1
        assert stats["active_entries"] == 1
        assert stats["expired_entries"] == 0
    
    def test_cleanup_expired_cache(self):
        """Test cleanup of expired cache entries."""
        # Set short TTL
        self.factory.config.cache_ttl_seconds = 1
        
        # Register template
        self.factory.register_template(
            name="test_template",
            template_class=MockTemplate,
            template_type=TemplateType.STANDUP
        )
        
        # Create template
        self.factory.create_template(TemplateType.STANDUP)
        assert len(self.factory._cache) == 1
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Cleanup expired entries
        cleaned = self.factory.cleanup_expired_cache()
        assert cleaned == 1
        assert len(self.factory._cache) == 0
    
    def test_template_creation_error_handling(self):
        """Test error handling during template creation."""
        class FailingTemplate(SlackMessageTemplate):
            def __init__(self, *args, **kwargs):
                raise ValueError("Template creation failed")
            
            def _create_message_blocks(self, data):
                return []
        
        # Register failing template
        self.factory.register_template(
            name="failing_template",
            template_class=FailingTemplate,
            template_type=TemplateType.STANDUP
        )
        
        # Should raise TemplateError
        with pytest.raises(TemplateError, match="Template creation failed"):
            self.factory.create_template(TemplateType.STANDUP)
    
    def test_metrics_disabled(self):
        """Test behavior when metrics are disabled."""
        # Create factory with metrics disabled
        config = FactoryConfig(enable_metrics=False)
        factory = MessageTemplateFactory(config)
        
        # Register template
        factory.register_template(
            name="test_template",
            template_class=MockTemplate,
            template_type=TemplateType.STANDUP
        )
        
        # Create template
        factory.create_template(TemplateType.STANDUP)
        
        # Should have no metrics
        metrics = factory.get_template_metrics()
        assert len(metrics) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])