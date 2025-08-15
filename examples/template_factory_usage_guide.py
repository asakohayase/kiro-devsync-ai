"""
Template Factory Usage Guide
Comprehensive guide for using the MessageTemplateFactory for dynamic template creation.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta

from devsync_ai.core.template_factory import MessageTemplateFactory
from devsync_ai.core.message_formatter import TemplateConfig, SlackMessage
from tests.test_data_generators import TestDataFactory, TestDataConfig, DataScenario


class TemplateFactoryGuide:
    """Guide for using the template factory effectively."""
    
    def __init__(self):
        """Initialize the factory guide with default configuration."""
        self.config = TemplateConfig(
            team_id="demo_team",
            branding={
                "team_name": "Demo Team",
                "logo_emoji": "🎯",
                "primary_color": "#2E86AB",
                "accent_color": "#A23B72"
            },
            interactive_elements=True,
            accessibility_mode=False,
            caching_enabled=True
        )
        self.factory = MessageTemplateFactory(config=self.config)
    
    def basic_factory_usage(self):
        """Demonstrate basic factory usage patterns."""
        print("=== BASIC FACTORY USAGE ===\n")
        
        # 1. Simple template creation
        print("1. Creating templates by type:")
        template_types = ["standup", "pr_opened", "jira_status_change", "build_failure"]
        
        for template_type in template_types:
            try:
                template = self.factory.create_template(template_type)
                print(f"✅ Created {template_type}: {template.__class__.__name__}")
            except Exception as e:
                print(f"❌ Failed to create {template_type}: {e}")
        
        print()
        
        # 2. Template with custom configuration
        print("2. Template with custom configuration:")
        custom_config = TemplateConfig(
            team_id="custom_team",
            branding={"team_name": "Custom Team", "logo_emoji": "⚡"},
            interactive_elements=False
        )
        
        custom_factory = MessageTemplateFactory(config=custom_config)
        template = custom_factory.create_template("standup")
        print(f"✅ Created custom standup template: {template.__class__.__name__}")
        print()
    
    def event_driven_usage(self):
        """Demonstrate event-driven template selection."""
        print("=== EVENT-DRIVEN USAGE ===\n")
        
        # Simulate incoming events
        events = [
            {
                "type": "github.pull_request",
                "action": "opened",
                "data": {
                    "pr": {
                        "number": 123,
                        "title": "Add new feature",
                        "author": "developer1",
                        "url": "https://github.com/repo/pull/123"
                    }
                }
            },
            {
                "type": "jira.issue",
                "action": "status_changed",
                "data": {
                    "ticket": {
                        "key": "PROJ-456",
                        "summary": "Fix critical bug",
                        "status": {"from": "To Do", "to": "In Progress"}
                    },
                    "change_type": "status_change"
                }
            },
            {
                "type": "ci.build",
                "action": "failed",
                "data": {
                    "alert": {
                        "id": "BUILD-789",
                        "type": "build_failure",
                        "severity": "high",
                        "title": "Main branch build failed"
                    }
                }
            }
        ]
        
        print("Processing incoming events:")
        for i, event in enumerate(events, 1):
            template_type = self._map_event_to_template(event)
            
            try:
                template = self.factory.create_template(template_type)
                message = template.format_message(event["data"])
                
                print(f"{i}. {event['type']}.{event['action']} → {template_type}")
                print(f"   Generated message with {len(message.blocks)} blocks")
                print(f"   Fallback: '{message.text[:60]}...'")
                
            except Exception as e:
                print(f"{i}. ❌ Failed to process {event['type']}: {e}")
        
        print()
    
    def batch_processing_usage(self):
        """Demonstrate batch processing capabilities."""
        print("=== BATCH PROCESSING USAGE ===\n")
        
        # Generate test data for batch processing
        test_config = TestDataConfig(scenario=DataScenario.COMPLETE)
        data_factory = TestDataFactory()
        
        # Create mixed batch of events
        batch_events = []
        
        # Add standup events
        standup_gen = data_factory.create_generator("standup", test_config)
        for i in range(3):
            data = standup_gen.generate_standup_data()
            batch_events.append(("standup", data))
        
        # Add PR events
        pr_gen = data_factory.create_generator("pr", test_config)
        for i in range(5):
            data = pr_gen.generate_pr_data()
            template_type = f"pr_{data['action']}"
            batch_events.append((template_type, data))
        
        # Add JIRA events
        jira_gen = data_factory.create_generator("jira", test_config)
        for i in range(4):
            data = jira_gen.generate_jira_data()
            template_type = f"jira_{data['change_type']}"
            batch_events.append((template_type, data))
        
        print(f"Processing batch of {len(batch_events)} events:")
        
        # Process batch
        start_time = datetime.now()
        messages = self.factory.process_batch(batch_events)
        processing_time = datetime.now() - start_time
        
        print(f"✅ Processed {len(messages)} messages in {processing_time.total_seconds():.3f}s")
        print(f"   Average: {processing_time.total_seconds() * 1000 / len(messages):.2f}ms per message")
        
        # Show summary by template type
        template_counts = {}
        for template_type, _ in batch_events:
            template_counts[template_type] = template_counts.get(template_type, 0) + 1
        
        print("\nBatch summary:")
        for template_type, count in sorted(template_counts.items()):
            print(f"   {template_type}: {count} messages")
        
        print()
    
    def caching_and_performance_usage(self):
        """Demonstrate caching and performance features."""
        print("=== CACHING AND PERFORMANCE ===\n")
        
        # Enable caching
        cached_config = TemplateConfig(
            team_id="cached_team",
            caching_enabled=True,
            cache_ttl=300  # 5 minutes
        )
        cached_factory = MessageTemplateFactory(config=cached_config)
        
        # Test data
        test_data = {
            "date": "2025-08-14",
            "team": "Performance Test Team",
            "team_members": [
                {
                    "name": "Test User",
                    "yesterday": ["Task 1"],
                    "today": ["Task 2"],
                    "blockers": []
                }
            ]
        }
        
        print("1. Cache Performance Test:")
        
        # First call (cache miss)
        start_time = datetime.now()
        template1 = cached_factory.create_template("standup")
        message1 = template1.format_message(test_data)
        first_call_time = datetime.now() - start_time
        
        # Second call (cache hit)
        start_time = datetime.now()
        template2 = cached_factory.create_template("standup")
        message2 = template2.format_message(test_data)
        second_call_time = datetime.now() - start_time
        
        print(f"   First call (cache miss): {first_call_time.total_seconds() * 1000:.2f}ms")
        print(f"   Second call (cache hit): {second_call_time.total_seconds() * 1000:.2f}ms")
        print(f"   Speed improvement: {first_call_time.total_seconds() / second_call_time.total_seconds():.1f}x")
        
        # Cache statistics
        cache_stats = cached_factory.get_cache_stats()
        print(f"   Cache hits: {cache_stats.get('hits', 0)}")
        print(f"   Cache misses: {cache_stats.get('misses', 0)}")
        print()
        
        print("2. Memory Usage Test:")
        import tracemalloc
        
        tracemalloc.start()
        
        # Create many templates
        templates = []
        for i in range(100):
            template = cached_factory.create_template("standup")
            templates.append(template)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        print(f"   Created 100 templates")
        print(f"   Memory usage: {current / 1024 / 1024:.2f}MB current, {peak / 1024 / 1024:.2f}MB peak")
        print()
    
    def error_handling_and_fallbacks(self):
        """Demonstrate error handling and fallback mechanisms."""
        print("=== ERROR HANDLING AND FALLBACKS ===\n")
        
        print("1. Invalid Template Type:")
        try:
            template = self.factory.create_template("invalid_template_type")
            print("❌ Should have failed for invalid template type")
        except Exception as e:
            print(f"✅ Correctly handled invalid template type: {e}")
        
        print()
        
        print("2. Malformed Data Handling:")
        template = self.factory.create_template("standup")
        
        malformed_data_cases = [
            ({}, "Empty data"),
            ({"date": None, "team": None}, "Null values"),
            ({"date": 123, "team": ["not", "string"]}, "Wrong data types"),
            ({"date": "2025-08-14", "team_members": "not a list"}, "Type mismatch")
        ]
        
        for data, description in malformed_data_cases:
            try:
                message = template.format_message(data)
                print(f"✅ {description}: Generated fallback message ({len(message.blocks)} blocks)")
            except Exception as e:
                print(f"❌ {description}: Failed to handle - {e}")
        
        print()
        
        print("3. Graceful Degradation:")
        # Test with accessibility mode for fallbacks
        accessible_config = TemplateConfig(
            team_id="accessible_team",
            accessibility_mode=True,
            interactive_elements=False
        )
        accessible_factory = MessageTemplateFactory(config=accessible_config)
        accessible_template = accessible_factory.create_template("standup")
        
        test_data = {
            "date": "2025-08-14",
            "team": "Accessible Team",
            "team_members": []
        }
        
        message = accessible_template.format_message(test_data)
        print(f"✅ Accessible mode: {len(message.blocks)} blocks")
        print(f"   Detailed fallback text: '{message.text}'")
        print()
    
    def advanced_configuration_usage(self):
        """Demonstrate advanced configuration options."""
        print("=== ADVANCED CONFIGURATION ===\n")
        
        print("1. Team-Specific Configurations:")
        
        team_configs = {
            "engineering": TemplateConfig(
                team_id="engineering",
                branding={
                    "team_name": "⚙️ Engineering Team",
                    "primary_color": "#2E86AB",
                    "logo_emoji": "⚙️"
                },
                emoji_set={
                    "success": "✅",
                    "warning": "⚠️",
                    "error": "❌",
                    "in_progress": "🔄"
                },
                interactive_elements=True
            ),
            "design": TemplateConfig(
                team_id="design",
                branding={
                    "team_name": "🎨 Design Team",
                    "primary_color": "#A23B72",
                    "logo_emoji": "🎨"
                },
                emoji_set={
                    "success": "🎉",
                    "warning": "⚡",
                    "error": "🚨",
                    "in_progress": "🎯"
                },
                interactive_elements=True
            ),
            "qa": TemplateConfig(
                team_id="qa",
                branding={
                    "team_name": "🔍 QA Team",
                    "primary_color": "#F18F01",
                    "logo_emoji": "🔍"
                },
                accessibility_mode=True,  # QA team prefers accessible format
                interactive_elements=False
            )
        }
        
        test_data = {
            "date": "2025-08-14",
            "team": "Test Team",
            "team_members": []
        }
        
        for team_name, config in team_configs.items():
            factory = MessageTemplateFactory(config=config)
            template = factory.create_template("standup")
            message = template.format_message(test_data)
            
            print(f"   {team_name}: {len(message.blocks)} blocks, branding: {config.branding['team_name']}")
        
        print()
        
        print("2. Environment-Specific Configurations:")
        
        environments = {
            "development": TemplateConfig(
                team_id="dev_team",
                interactive_elements=True,
                caching_enabled=False,  # Disable caching in dev
                debug_mode=True
            ),
            "staging": TemplateConfig(
                team_id="staging_team",
                interactive_elements=True,
                caching_enabled=True,
                cache_ttl=300
            ),
            "production": TemplateConfig(
                team_id="prod_team",
                interactive_elements=True,
                caching_enabled=True,
                cache_ttl=3600,  # Longer cache in production
                performance_mode=True
            )
        }
        
        for env_name, config in environments.items():
            factory = MessageTemplateFactory(config=config)
            print(f"   {env_name}: caching={config.caching_enabled}, cache_ttl={getattr(config, 'cache_ttl', 'N/A')}")
        
        print()
    
    def _map_event_to_template(self, event: Dict[str, Any]) -> str:
        """Map incoming events to template types."""
        event_type = event["type"]
        action = event["action"]
        
        mapping = {
            ("github.pull_request", "opened"): "pr_opened",
            ("github.pull_request", "closed"): "pr_closed",
            ("github.pull_request", "merged"): "pr_merged",
            ("jira.issue", "status_changed"): "jira_status_change",
            ("jira.issue", "priority_changed"): "jira_priority_change",
            ("jira.issue", "comment_added"): "jira_comment_added",
            ("ci.build", "failed"): "build_failure",
            ("ci.deployment", "failed"): "deployment_issue",
            ("monitoring.alert", "triggered"): "service_outage"
        }
        
        return mapping.get((event_type, action), "generic_alert")


def main():
    """Run the template factory usage guide."""
    print("TEMPLATE FACTORY USAGE GUIDE")
    print("=" * 50)
    print()
    
    guide = TemplateFactoryGuide()
    
    try:
        guide.basic_factory_usage()
        guide.event_driven_usage()
        guide.batch_processing_usage()
        guide.caching_and_performance_usage()
        guide.error_handling_and_fallbacks()
        guide.advanced_configuration_usage()
        
        print("=" * 50)
        print("✅ Template Factory Usage Guide completed successfully!")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Guide execution failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()