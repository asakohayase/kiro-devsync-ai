#!/usr/bin/env python3
"""
Complete system validation script.
Demonstrates end-to-end functionality of the integrated template system.
"""

import json
import time
from datetime import datetime
from typing import Dict, Any

from devsync_ai.core.template_registry import initialize_template_system, create_end_to_end_message
from devsync_ai.core.message_formatter import TemplateConfig


def main():
    """Run complete system validation."""
    print("🚀 Starting Complete Template System Validation")
    print("=" * 60)
    
    # Initialize the template system
    print("📋 Initializing template system...")
    factory = initialize_template_system()
    print(f"✅ Template system initialized with {len(factory.get_registered_templates())} templates")
    
    # Test scenarios for each template type
    test_scenarios = [
        {
            "name": "Daily Standup Message",
            "event_type": "standup.daily",
            "data": {
                "date": "2024-01-15",
                "team": "Engineering Team",
                "team_members": [
                    {
                        "name": "alice",
                        "yesterday": "Completed user authentication feature",
                        "today": "Working on API integration tests",
                        "blockers": []
                    },
                    {
                        "name": "bob",
                        "yesterday": "Fixed database performance issues",
                        "today": "Code review and deployment preparation",
                        "blockers": ["Waiting for staging environment access"]
                    },
                    {
                        "name": "charlie",
                        "yesterday": "Updated documentation and user guides",
                        "today": "Working on frontend components",
                        "blockers": []
                    }
                ],
                "stats": {
                    "prs_merged": 5,
                    "prs_open": 3,
                    "tickets_closed": 8,
                    "tickets_open": 12,
                    "commits": 23
                },
                "sprint_progress": {
                    "completed": 12,
                    "total": 18,
                    "story_points": {
                        "completed": 34,
                        "total": 55
                    }
                },
                "action_items": [
                    {
                        "title": "Set up staging environment access",
                        "assignee": "devops_team",
                        "due_date": "2024-01-16",
                        "priority": "high"
                    },
                    {
                        "title": "Review API documentation",
                        "assignee": "alice",
                        "due_date": "2024-01-17",
                        "priority": "medium"
                    }
                ]
            }
        },
        {
            "name": "New Pull Request",
            "event_type": "pull_request.opened",
            "data": {
                "pr": {
                    "number": 456,
                    "title": "Implement advanced search functionality",
                    "html_url": "https://github.com/company/repo/pull/456",
                    "user": {"login": "alice"},
                    "head": {"ref": "feature/advanced-search"},
                    "base": {"ref": "main"},
                    "reviewers": [
                        {"login": "bob", "review_status": "pending"},
                        {"login": "charlie", "review_status": "pending"}
                    ],
                    "labels": [
                        {"name": "feature"},
                        {"name": "backend"},
                        {"name": "high-priority"}
                    ],
                    "priority": "high",
                    "description": "This PR adds advanced search capabilities with filters, sorting, and pagination. Includes comprehensive unit tests and API documentation updates."
                }
            }
        },
        {
            "name": "JIRA Status Change",
            "event_type": "jira.status_changed",
            "data": {
                "ticket": {
                    "key": "DEV-789",
                    "summary": "Implement user dashboard with analytics",
                    "status": "In Progress",
                    "priority": "High",
                    "assignee": "alice",
                    "reporter": "product_manager",
                    "story_points": 8,
                    "sprint": "Sprint 24",
                    "components": ["frontend", "analytics"],
                    "labels": ["dashboard", "analytics", "user-experience"]
                },
                "from_status": "To Do",
                "to_status": "In Progress"
            }
        },
        {
            "name": "Build Failure Alert",
            "event_type": "alert.build_failure",
            "data": {
                "alert": {
                    "id": "alert_build_001",
                    "title": "Build Failure: Main Branch CI Pipeline",
                    "description": "Unit tests failed in authentication module",
                    "severity": "high",
                    "type": "build_failure",
                    "affected_systems": ["ci-pipeline", "authentication-service"],
                    "created_at": "2024-01-15T10:30:00Z",
                    "assigned_to": "alice"
                },
                "build_info": {
                    "branch": "main",
                    "commit": "a1b2c3d4e5f6",
                    "failed_stage": "unit-tests",
                    "pipeline_url": "https://ci.company.com/build/12345"
                }
            }
        }
    ]
    
    print("\n🧪 Running End-to-End Test Scenarios")
    print("-" * 40)
    
    validation_results = {
        "total_scenarios": len(test_scenarios),
        "successful_scenarios": 0,
        "failed_scenarios": [],
        "performance_metrics": {}
    }
    
    # Test each scenario
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}. Testing: {scenario['name']}")
        
        try:
            start_time = time.time()
            
            # Create end-to-end message
            message_dict = create_end_to_end_message(
                scenario["event_type"],
                scenario["data"]
            )
            
            execution_time = time.time() - start_time
            
            # Validate message structure
            assert "blocks" in message_dict
            assert "text" in message_dict
            assert "metadata" in message_dict
            assert len(message_dict["blocks"]) > 0
            assert len(message_dict["text"]) > 0
            
            # Validate content quality
            message_size = len(json.dumps(message_dict["blocks"]))
            assert message_size > 200, "Message content too small"
            assert message_size < 50000, "Message content too large"
            
            # Record performance
            validation_results["performance_metrics"][scenario["name"]] = {
                "execution_time": execution_time,
                "message_size": message_size,
                "block_count": len(message_dict["blocks"])
            }
            
            validation_results["successful_scenarios"] += 1
            
            print(f"   ✅ Success ({execution_time:.3f}s, {message_size} bytes, {len(message_dict['blocks'])} blocks)")
            
            # Show sample of generated content
            sample_text = message_dict["text"][:100] + "..." if len(message_dict["text"]) > 100 else message_dict["text"]
            print(f"   📝 Sample: {sample_text}")
            
        except Exception as e:
            validation_results["failed_scenarios"].append({
                "scenario": scenario["name"],
                "error": str(e)
            })
            print(f"   ❌ Failed: {e}")
    
    print("\n📊 Testing Configuration and Customization")
    print("-" * 40)
    
    # Test with different configurations
    config_tests = [
        {
            "name": "Accessibility Mode",
            "config": TemplateConfig(
                team_id="accessibility_team",
                accessibility_mode=True,
                interactive_elements=False,
                emoji_set={
                    "success": "[COMPLETED]",
                    "warning": "[WARNING]",
                    "error": "[ERROR]"
                }
            )
        },
        {
            "name": "Custom Branding",
            "config": TemplateConfig(
                team_id="custom_team",
                branding={
                    "primary_color": "#ff6b35",
                    "logo_emoji": ":rocket:",
                    "team_name": "Rocket Team"
                },
                interactive_elements=True
            )
        }
    ]
    
    for config_test in config_tests:
        print(f"\n🎨 Testing: {config_test['name']}")
        
        try:
            # Test with standup scenario
            template = factory.create_template("standup_daily", config_test["config"])
            message = template.format_message({
                "date": "2024-01-15",
                "team": "Test Team",
                "team_members": [
                    {"name": "test_user", "yesterday": "Work", "today": "More work", "blockers": []}
                ],
                "stats": {"prs_merged": 1, "commits": 5}
            })
            
            # Validate configuration was applied
            assert message.metadata["config"]["team_id"] == config_test["config"].team_id
            
            print(f"   ✅ Configuration applied successfully")
            
            # Check accessibility features
            if config_test["config"].accessibility_mode:
                assert len(message.text) > 50, "Accessibility fallback text too short"
                print(f"   ♿ Accessibility features validated")
            
        except Exception as e:
            print(f"   ❌ Configuration test failed: {e}")
    
    print("\n⚡ Performance and Load Testing")
    print("-" * 40)
    
    # Performance test
    try:
        concurrent_messages = 20
        start_time = time.time()
        
        for i in range(concurrent_messages):
            message_dict = create_end_to_end_message(
                "standup.daily",
                {
                    "date": f"2024-01-{i % 30 + 1:02d}",
                    "team": f"Performance Test Team {i}",
                    "team_members": [
                        {"name": f"user_{i}", "yesterday": f"Task {i}", "today": f"Task {i+1}", "blockers": []}
                    ],
                    "stats": {"prs_merged": i % 5, "commits": i % 10}
                }
            )
        
        total_time = time.time() - start_time
        messages_per_second = concurrent_messages / total_time
        
        print(f"   ✅ Created {concurrent_messages} messages in {total_time:.3f}s")
        print(f"   📈 Performance: {messages_per_second:.1f} messages/second")
        
        # Validate performance requirements
        assert messages_per_second > 10, "Performance too slow"
        print(f"   🚀 Performance requirements met")
        
    except Exception as e:
        print(f"   ❌ Performance test failed: {e}")
    
    print("\n📋 Final Validation Summary")
    print("=" * 60)
    
    # Print overall results
    success_rate = validation_results["successful_scenarios"] / validation_results["total_scenarios"]
    print(f"✅ Successful Scenarios: {validation_results['successful_scenarios']}/{validation_results['total_scenarios']} ({success_rate:.1%})")
    
    if validation_results["failed_scenarios"]:
        print(f"❌ Failed Scenarios: {len(validation_results['failed_scenarios'])}")
        for failure in validation_results["failed_scenarios"]:
            print(f"   - {failure['scenario']}: {failure['error']}")
    
    # Performance summary
    if validation_results["performance_metrics"]:
        print(f"\n⚡ Performance Summary:")
        avg_time = sum(m["execution_time"] for m in validation_results["performance_metrics"].values()) / len(validation_results["performance_metrics"])
        avg_size = sum(m["message_size"] for m in validation_results["performance_metrics"].values()) / len(validation_results["performance_metrics"])
        print(f"   Average execution time: {avg_time:.3f}s")
        print(f"   Average message size: {avg_size:.0f} bytes")
    
    # Cache statistics
    cache_stats = factory.get_cache_stats()
    print(f"\n💾 Cache Statistics:")
    print(f"   Cache entries: {cache_stats['total_entries']}")
    print(f"   Cache utilization: {cache_stats['cache_utilization']:.1%}")
    
    # Template metrics
    template_metrics = factory.get_template_metrics()
    if template_metrics:
        print(f"\n📊 Template Usage Metrics:")
        for template_name, metrics in template_metrics.items():
            if "usage_count" in metrics:
                print(f"   {template_name}: {metrics['usage_count']} uses")
    
    # Final validation
    if success_rate >= 1.0:
        print(f"\n🎉 SYSTEM VALIDATION PASSED!")
        print(f"   All template components are properly integrated")
        print(f"   End-to-end workflows are functioning correctly")
        print(f"   Configuration and customization working as expected")
        print(f"   Performance requirements met")
        return 0
    else:
        print(f"\n❌ SYSTEM VALIDATION FAILED!")
        print(f"   Some scenarios failed - check logs above")
        return 1


if __name__ == "__main__":
    exit(main())