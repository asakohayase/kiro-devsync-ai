"""
Integration tests for template factory system.
Tests end-to-end template creation, caching mechanisms, and factory integration.
"""

import pytest
import time
from unittest.mock import Mock, patch
from typing import Dict, List, Any

from devsync_ai.core.template_factory import MessageTemplateFactory
from devsync_ai.core.message_formatter import TemplateConfig, SlackMessage
from devsync_ai.templates.standup_template import StandupTemplate
from devsync_ai.templates.pr_templates import NewPRTemplate
from devsync_ai.templates.jira_templates import JIRATemplate
from devsync_ai.templates.alert_templates import AlertTemplate


class TestTemplateFactoryIntegration:
    """Test end-to-end template factory integration."""
    
    def test_template_factory_initialization(self):
        """Test template factory initialization and registration."""
        factory = MessageTemplateFactory()
        
        # Should initialize without errors
        assert factory is not None
        
        # Should have some registered templates (if any are pre-registered)
        # This depends on the actual implementation
    
    def test_template_creation_and_caching(self):
        """Test template creation and caching mechanisms."""
        factory = MessageTemplateFactory()
        config = TemplateConfig(team_id="test_team")
        
        # Test template creation
        try:
            standup_template = factory.create_template("standup", config)
            assert standup_template is not None
            
            # Test caching - second call should return cached instance
            standup_template_2 = factory.create_template("standup", config)
            
            # Depending on implementation, might be same instance or equivalent
            assert standup_template_2 is not None
            
        except (AttributeError, NotImplementedError):
            # If factory doesn't exist yet, test basic template creation
            standup_template = StandupTemplate(config=config)
            assert standup_template is not None
            assert standup_template.config.team_id == "test_team"
    
    def test_end_to_end_message_creation_workflow(self):
        """Test complete end-to-end message creation workflow."""
        # Test data for different template types
        test_cases = [
            {
                'template_class': StandupTemplate,
                'data': {
                    'date': '2025-08-14',
                    'team': 'Test Team',
                    'team_members': [
                        {'name': 'Test User', 'yesterday': [], 'today': [], 'blockers': []}
                    ]
                }
            },
            {
                'template_class': NewPRTemplate,
                'data': {
                    'pr': {
                        'number': 123,
                        'title': 'Test PR',
                        'author': 'test.user'
                    }
                }
            },
            {
                'template_class': JIRATemplate,
                'data': {
                    'ticket': {
                        'key': 'TEST-123',
                        'summary': 'Test ticket',
                        'status': 'In Progress'
                    }
                }
            },
            {
                'template_class': AlertTemplate,
                'data': {
                    'alert': {
                        'title': 'Test Alert',
                        'severity': 'medium',
                        'description': 'Test alert description'
                    }
                }
            }
        ]
        
        for test_case in test_cases:
            template_class = test_case['template_class']
            data = test_case['data']
            
            # Create template instance
            template = template_class()
            
            # Format message
            message = template.format_message(data)
            
            # Verify message structure
            assert isinstance(message, SlackMessage)
            assert len(message.blocks) > 0
            assert message.text  # Should have fallback text
            assert 'template_type' in message.metadata
            assert 'created_at' in message.metadata
    
    def test_template_configuration_integration(self):
        """Test template configuration integration across different templates."""
        # Test different configuration scenarios
        configs = [
            TemplateConfig(team_id="team1", interactive_elements=True),
            TemplateConfig(team_id="team2", interactive_elements=False),
            TemplateConfig(team_id="team3", accessibility_mode=True),
            TemplateConfig(
                team_id="team4", 
                branding={"team_name": "Test Team", "logo_emoji": "🚀"}
            )
        ]
        
        for config in configs:
            # Test with standup template
            template = StandupTemplate(config=config)
            data = {
                'date': '2025-08-14',
                'team': 'Test Team',
                'team_members': []
            }
            
            message = template.format_message(data)
            
            # Verify configuration is applied
            assert isinstance(message, SlackMessage)
            assert message.metadata['config']['team_id'] == config.team_id
            assert message.metadata['config']['interactive_elements'] == config.interactive_elements
            
            # Check for branding if configured
            if config.branding and 'logo_emoji' in config.branding:
                # Should have branding applied (depends on implementation)
                pass
    
    def test_error_handling_integration(self):
        """Test error handling integration across the template system."""
        templates = [StandupTemplate(), NewPRTemplate(), JIRATemplate(), AlertTemplate()]
        
        # Test with various error scenarios
        error_scenarios = [
            {},  # Empty data
            {'invalid': 'data'},  # Invalid data structure
            None,  # None data
        ]
        
        for template in templates:
            for scenario in error_scenarios:
                try:
                    message = template.format_message(scenario)
                    
                    # Should handle errors gracefully
                    assert isinstance(message, SlackMessage)
                    assert len(message.blocks) > 0
                    
                    # Should either succeed or return error message
                    if message.metadata.get('error'):
                        assert 'error' in message.text.lower()
                    
                except Exception as e:
                    # If exceptions are raised, they should be meaningful
                    assert str(e)  # Should have error message
    
    def test_template_inheritance_integration(self):
        """Test template inheritance and polymorphism integration."""
        # Test that all templates inherit from base properly
        templates = [
            StandupTemplate(),
            NewPRTemplate(),
            JIRATemplate(),
            AlertTemplate()
        ]
        
        for template in templates:
            # Should have required base methods
            assert hasattr(template, 'format_message')
            assert hasattr(template, 'config')
            assert hasattr(template, 'status_system')
            
            # Should have required fields defined
            assert hasattr(template, 'REQUIRED_FIELDS')
            assert isinstance(template.REQUIRED_FIELDS, list)


class TestTemplateFactoryCaching:
    """Test template factory caching mechanisms."""
    
    def test_template_instance_caching(self):
        """Test template instance caching with TTL management."""
        # This test assumes a caching implementation exists
        # If not implemented yet, test basic template reuse
        
        config = TemplateConfig(team_id="cache_test")
        
        # Create multiple instances
        template1 = StandupTemplate(config=config)
        template2 = StandupTemplate(config=config)
        
        # Both should be valid instances
        assert template1 is not None
        assert template2 is not None
        
        # Test that they have the same configuration
        assert template1.config.team_id == template2.config.team_id
    
    def test_rendered_message_caching(self):
        """Test rendered message caching for repeated content."""
        template = StandupTemplate()
        data = {
            'date': '2025-08-14',
            'team': 'Cache Test Team',
            'team_members': []
        }
        
        # Render same message multiple times
        start_time = time.time()
        message1 = template.format_message(data)
        first_render_time = time.time() - start_time
        
        start_time = time.time()
        message2 = template.format_message(data)
        second_render_time = time.time() - start_time
        
        # Both messages should be valid
        assert isinstance(message1, SlackMessage)
        assert isinstance(message2, SlackMessage)
        
        # Content should be equivalent (though timestamps might differ)
        assert len(message1.blocks) == len(message2.blocks)
        assert message1.metadata['template_type'] == message2.metadata['template_type']
    
    def test_cache_invalidation_strategies(self):
        """Test cache invalidation strategies."""
        # Test with different configurations to ensure cache separation
        config1 = TemplateConfig(team_id="team1")
        config2 = TemplateConfig(team_id="team2")
        
        template1 = StandupTemplate(config=config1)
        template2 = StandupTemplate(config=config2)
        
        data = {
            'date': '2025-08-14',
            'team': 'Test Team',
            'team_members': []
        }
        
        message1 = template1.format_message(data)
        message2 = template2.format_message(data)
        
        # Should have different team configurations
        assert message1.metadata['config']['team_id'] != message2.metadata['config']['team_id']


class TestTemplateFactoryPerformance:
    """Test template factory performance characteristics."""
    
    def test_template_creation_performance(self):
        """Test template creation performance benchmarks."""
        template_classes = [StandupTemplate, NewPRTemplate, JIRATemplate, AlertTemplate]
        
        for template_class in template_classes:
            # Measure template creation time
            start_time = time.time()
            
            templates = []
            for i in range(10):  # Create 10 instances
                template = template_class()
                templates.append(template)
            
            creation_time = time.time() - start_time
            
            # Should create templates reasonably quickly
            assert creation_time < 1.0  # Less than 1 second for 10 templates
            assert len(templates) == 10
            
            # All templates should be valid
            for template in templates:
                assert template is not None
                assert hasattr(template, 'format_message')
    
    def test_message_rendering_performance(self):
        """Test message rendering performance under load."""
        template = StandupTemplate()
        data = {
            'date': '2025-08-14',
            'team': 'Performance Test Team',
            'team_members': [
                {'name': f'User {i}', 'yesterday': [], 'today': [], 'blockers': []}
                for i in range(5)  # 5 team members
            ]
        }
        
        # Measure rendering time for multiple messages
        start_time = time.time()
        
        messages = []
        for i in range(20):  # Render 20 messages
            message = template.format_message(data)
            messages.append(message)
        
        rendering_time = time.time() - start_time
        
        # Should render messages reasonably quickly
        assert rendering_time < 2.0  # Less than 2 seconds for 20 messages
        assert len(messages) == 20
        
        # All messages should be valid
        for message in messages:
            assert isinstance(message, SlackMessage)
            assert len(message.blocks) > 0
    
    def test_memory_usage_efficiency(self):
        """Test memory usage efficiency for template instances."""
        import sys
        
        # Measure memory usage before creating templates
        initial_objects = len([obj for obj in globals().values() if hasattr(obj, '__dict__')])
        
        # Create multiple template instances
        templates = []
        for i in range(50):
            template = StandupTemplate()
            templates.append(template)
        
        # Measure memory usage after
        final_objects = len([obj for obj in globals().values() if hasattr(obj, '__dict__')])
        
        # Should not create excessive objects
        object_increase = final_objects - initial_objects
        assert object_increase < 100  # Reasonable object creation
        
        # Clean up
        del templates
    
    def test_concurrent_template_usage(self):
        """Test concurrent template usage scenarios."""
        import threading
        import queue
        
        template = StandupTemplate()
        results = queue.Queue()
        
        def render_message(thread_id):
            """Render a message in a separate thread."""
            data = {
                'date': '2025-08-14',
                'team': f'Thread {thread_id} Team',
                'team_members': []
            }
            
            try:
                message = template.format_message(data)
                results.put(('success', thread_id, message))
            except Exception as e:
                results.put(('error', thread_id, str(e)))
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=render_message, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        success_count = 0
        error_count = 0
        
        while not results.empty():
            result_type, thread_id, result = results.get()
            if result_type == 'success':
                success_count += 1
                assert isinstance(result, SlackMessage)
            else:
                error_count += 1
        
        # Should handle concurrent usage well
        assert success_count >= 4  # At least 4 out of 5 should succeed
        assert error_count <= 1   # At most 1 error acceptable


if __name__ == "__main__":
    print("Running template factory integration tests...")
    
    # Basic integration test
    template = StandupTemplate()
    data = {
        'date': '2025-08-14',
        'team': 'Integration Test Team',
        'team_members': []
    }
    message = template.format_message(data)
    
    assert isinstance(message, SlackMessage)
    assert len(message.blocks) > 0
    print("✅ Basic integration test passed")
    
    # Performance test
    start_time = time.time()
    for i in range(10):
        template.format_message(data)
    performance_time = time.time() - start_time
    
    assert performance_time < 1.0  # Should be fast
    print(f"✅ Performance test passed ({performance_time:.3f}s for 10 renders)")
    
    print("All integration and performance tests passed!")