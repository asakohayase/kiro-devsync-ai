"""
Simple Usage Examples
Basic examples demonstrating how to use the Slack Message Templates system.
"""

from typing import Dict, Any
from datetime import datetime

# Import available template classes
try:
    from devsync_ai.templates.standup_template import StandupTemplate
    from devsync_ai.core.message_formatter import TemplateConfig
    TEMPLATES_AVAILABLE = True
except ImportError:
    print("Templates not available - using mock implementations")
    TEMPLATES_AVAILABLE = False
    
    # Mock implementations for demonstration
    class MockTemplateConfig:
        def __init__(self, team_id: str, **kwargs):
            self.team_id = team_id
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class MockSlackMessage:
        def __init__(self, blocks=None, text=""):
            self.blocks = blocks or []
            self.text = text
    
    class MockStandupTemplate:
        def __init__(self, config=None):
            self.config = config
        
        def format_message(self, data):
            return MockSlackMessage(
                blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "Mock standup message"}}],
                text="Mock standup fallback text"
            )
    
    TemplateConfig = MockTemplateConfig
    StandupTemplate = MockStandupTemplate


def basic_standup_example():
    """Basic standup template usage example."""
    print("=== BASIC STANDUP EXAMPLE ===\n")
    
    # Create basic configuration
    config = TemplateConfig(
        team_id="engineering",
        branding={"team_name": "Engineering Team", "logo_emoji": "⚙️"},
        interactive_elements=True
    )
    
    # Create template
    template = StandupTemplate(config=config)
    
    # Sample standup data
    standup_data = {
        "date": "2025-08-14",
        "team": "Engineering Team",
        "team_members": [
            {
                "name": "Alice Johnson",
                "status": "active",
                "yesterday": [
                    "Completed user authentication API",
                    "Fixed bug in payment processing"
                ],
                "today": [
                    "Implement password reset functionality",
                    "Start work on dashboard redesign"
                ],
                "blockers": []
            },
            {
                "name": "Bob Smith",
                "status": "active",
                "yesterday": [
                    "Database migration for user profiles"
                ],
                "today": [
                    "Continue search optimization"
                ],
                "blockers": [
                    "Waiting for API documentation from external team"
                ]
            }
        ],
        "stats": {
            "prs_merged": 8,
            "prs_open": 12,
            "tickets_completed": 15,
            "tickets_in_progress": 23,
            "commits": 47
        },
        "action_items": [
            {
                "description": "Schedule architecture review meeting",
                "assignee": "Alice Johnson",
                "due_date": "2025-08-16"
            }
        ]
    }
    
    # Format message
    try:
        message = template.format_message(standup_data)
        print(f"✅ Generated standup message with {len(message.blocks)} blocks")
        print(f"Fallback text: {message.text[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Failed to generate standup message: {e}")
        return False


def minimal_standup_example():
    """Minimal standup example with basic data."""
    print("\n=== MINIMAL STANDUP EXAMPLE ===\n")
    
    config = TemplateConfig(team_id="minimal_team")
    template = StandupTemplate(config=config)
    
    # Minimal data
    minimal_data = {
        "date": "2025-08-14",
        "team": "Minimal Team",
        "team_members": [
            {
                "name": "Developer",
                "yesterday": ["Worked on features"],
                "today": ["Continue development"],
                "blockers": []
            }
        ]
    }
    
    try:
        message = template.format_message(minimal_data)
        print(f"✅ Generated minimal message with {len(message.blocks)} blocks")
        print(f"Fallback text: {message.text[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Failed to generate minimal message: {e}")
        return False


def error_handling_example():
    """Demonstrate error handling with malformed data."""
    print("\n=== ERROR HANDLING EXAMPLE ===\n")
    
    config = TemplateConfig(team_id="error_test")
    template = StandupTemplate(config=config)
    
    # Test cases with various issues
    test_cases = [
        ("Empty data", {}),
        ("Missing team", {"date": "2025-08-14"}),
        ("Null values", {"date": None, "team": None, "team_members": None}),
        ("Wrong types", {"date": 123, "team": ["not", "string"], "team_members": "not a list"}),
    ]
    
    for description, test_data in test_cases:
        try:
            message = template.format_message(test_data)
            print(f"✅ {description}: Handled gracefully ({len(message.blocks)} blocks)")
        except Exception as e:
            print(f"❌ {description}: Failed to handle - {e}")


def configuration_examples():
    """Demonstrate different configuration options."""
    print("\n=== CONFIGURATION EXAMPLES ===\n")
    
    # Different team configurations
    configurations = [
        ("Basic", TemplateConfig(team_id="basic")),
        ("Engineering", TemplateConfig(
            team_id="engineering",
            branding={"team_name": "⚙️ Engineering Team", "logo_emoji": "⚙️"},
            interactive_elements=True
        )),
        ("Design", TemplateConfig(
            team_id="design",
            branding={"team_name": "🎨 Design Team", "logo_emoji": "🎨"},
            emoji_set={"success": "🎉", "warning": "⚡", "error": "🚨"}
        )),
        ("Accessible", TemplateConfig(
            team_id="accessible",
            accessibility_mode=True,
            interactive_elements=False
        ))
    ]
    
    test_data = {
        "date": "2025-08-14",
        "team": "Test Team",
        "team_members": [
            {
                "name": "Test User",
                "yesterday": ["Test task"],
                "today": ["Another test"],
                "blockers": []
            }
        ]
    }
    
    for config_name, config in configurations:
        try:
            template = StandupTemplate(config=config)
            message = template.format_message(test_data)
            print(f"✅ {config_name} config: {len(message.blocks)} blocks")
        except Exception as e:
            print(f"❌ {config_name} config failed: {e}")


def batch_processing_example():
    """Demonstrate processing multiple messages."""
    print("\n=== BATCH PROCESSING EXAMPLE ===\n")
    
    config = TemplateConfig(team_id="batch_team")
    template = StandupTemplate(config=config)
    
    # Multiple days of standup data
    batch_data = []
    for day in range(1, 6):  # 5 days
        data = {
            "date": f"2025-08-{day:02d}",
            "team": f"Team {day}",
            "team_members": [
                {
                    "name": f"Developer {day}",
                    "yesterday": [f"Task {day}.1", f"Task {day}.2"],
                    "today": [f"Task {day+1}.1"],
                    "blockers": []
                }
            ],
            "stats": {
                "prs_merged": day * 2,
                "prs_open": day,
                "tickets_completed": day * 3,
                "commits": day * 5
            }
        }
        batch_data.append(data)
    
    # Process batch
    messages = []
    start_time = datetime.now()
    
    for i, data in enumerate(batch_data):
        try:
            message = template.format_message(data)
            messages.append(message)
        except Exception as e:
            print(f"❌ Failed to process item {i+1}: {e}")
    
    processing_time = datetime.now() - start_time
    
    print(f"✅ Processed {len(messages)} messages in {processing_time.total_seconds():.3f}s")
    print(f"Average: {processing_time.total_seconds() * 1000 / len(messages):.2f}ms per message")
    
    # Show summary
    total_blocks = sum(len(msg.blocks) for msg in messages)
    print(f"Total blocks generated: {total_blocks}")


def integration_simulation():
    """Simulate integration with external systems."""
    print("\n=== INTEGRATION SIMULATION ===\n")
    
    config = TemplateConfig(
        team_id="integration_team",
        branding={"team_name": "Integration Team", "logo_emoji": "🔗"}
    )
    template = StandupTemplate(config=config)
    
    # Simulate webhook data from different sources
    webhook_events = [
        {
            "source": "github",
            "data": {
                "date": "2025-08-14",
                "team": "GitHub Integration",
                "team_members": [
                    {
                        "name": "GitHub User",
                        "yesterday": ["Merged PR #123", "Reviewed PR #124"],
                        "today": ["Work on PR #125"],
                        "blockers": []
                    }
                ],
                "stats": {"prs_merged": 2, "prs_open": 3}
            }
        },
        {
            "source": "jira",
            "data": {
                "date": "2025-08-14",
                "team": "JIRA Integration",
                "team_members": [
                    {
                        "name": "JIRA User",
                        "yesterday": ["Completed PROJ-456"],
                        "today": ["Start PROJ-789"],
                        "blockers": ["Waiting for requirements"]
                    }
                ],
                "stats": {"tickets_completed": 1, "tickets_in_progress": 2}
            }
        }
    ]
    
    for event in webhook_events:
        try:
            message = template.format_message(event["data"])
            print(f"✅ {event['source']} integration: {len(message.blocks)} blocks")
        except Exception as e:
            print(f"❌ {event['source']} integration failed: {e}")


def performance_test():
    """Basic performance test."""
    print("\n=== PERFORMANCE TEST ===\n")
    
    config = TemplateConfig(team_id="performance_team")
    template = StandupTemplate(config=config)
    
    # Create test data with varying complexity
    test_data = {
        "date": "2025-08-14",
        "team": "Performance Test Team",
        "team_members": [
            {
                "name": f"User {i}",
                "yesterday": [f"Task {j}" for j in range(3)],
                "today": [f"Task {j+3}" for j in range(3)],
                "blockers": [f"Blocker {i}"] if i % 3 == 0 else []
            }
            for i in range(20)  # 20 team members
        ],
        "stats": {
            "prs_merged": 50,
            "prs_open": 30,
            "tickets_completed": 100,
            "tickets_in_progress": 75,
            "commits": 200
        },
        "action_items": [
            {
                "description": f"Action item {i}",
                "assignee": f"User {i % 20}",
                "due_date": "2025-08-15"
            }
            for i in range(10)
        ]
    }
    
    # Performance test
    iterations = 50
    start_time = datetime.now()
    
    for _ in range(iterations):
        try:
            message = template.format_message(test_data)
            assert len(message.blocks) > 0
        except Exception as e:
            print(f"❌ Performance test failed: {e}")
            return
    
    total_time = datetime.now() - start_time
    avg_time = total_time.total_seconds() / iterations
    
    print(f"✅ Performance test completed:")
    print(f"   {iterations} iterations in {total_time.total_seconds():.3f}s")
    print(f"   Average: {avg_time * 1000:.2f}ms per message")
    print(f"   Rate: {iterations / total_time.total_seconds():.1f} messages/second")


def main():
    """Run all simple usage examples."""
    print("SLACK MESSAGE TEMPLATES - SIMPLE USAGE EXAMPLES")
    print("=" * 60)
    
    if not TEMPLATES_AVAILABLE:
        print("⚠️  Using mock implementations - templates not available")
    
    print()
    
    examples = [
        basic_standup_example,
        minimal_standup_example,
        error_handling_example,
        configuration_examples,
        batch_processing_example,
        integration_simulation,
        performance_test
    ]
    
    results = []
    
    for example in examples:
        try:
            result = example()
            results.append(result if result is not None else True)
        except Exception as e:
            print(f"❌ Example failed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"✅ Successful examples: {sum(results)}")
    print(f"❌ Failed examples: {len(results) - sum(results)}")
    print("=" * 60)


if __name__ == "__main__":
    main()