"""
Edge case test data generators for comprehensive template testing.
Focuses on boundary conditions, malformed data, and error scenarios.
"""

import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from tests.test_data_generators import MockDataGenerator, TestDataConfig, DataScenario


class EdgeCaseDataGenerator(MockDataGenerator):
    """Generator for edge case and boundary condition testing."""
    
    def __init__(self):
        config = TestDataConfig(
            scenario=DataScenario.EDGE_CASE,
            include_nulls=True,
            include_empty_strings=True,
            include_unicode=True,
            include_long_text=True
        )
        super().__init__(config)
    
    def generate_null_and_empty_cases(self, template_type: str) -> List[Dict[str, Any]]:
        """Generate test cases with null and empty values."""
        cases = []
        
        if template_type == "standup":
            cases.extend([
                # Completely empty
                {},
                # Null values
                {
                    "date": None,
                    "team": None,
                    "team_members": None,
                    "stats": None,
                    "action_items": None
                },
                # Empty strings
                {
                    "date": "",
                    "team": "",
                    "team_members": [],
                    "stats": {},
                    "action_items": []
                },
                # Mixed null and empty
                {
                    "date": "2025-08-14",
                    "team": None,
                    "team_members": [
                        {
                            "name": "",
                            "yesterday": None,
                            "today": [],
                            "blockers": None
                        }
                    ],
                    "stats": None,
                    "action_items": []
                }
            ])
        
        elif template_type == "pr":
            cases.extend([
                # Completely empty
                {},
                # Null PR
                {"pr": None, "action": "opened"},
                # Empty PR
                {"pr": {}, "action": "opened"},
                # Null values in PR
                {
                    "pr": {
                        "id": None,
                        "title": None,
                        "author": None,
                        "reviewers": None,
                        "status": None
                    },
                    "action": None
                },
                # Empty strings in PR
                {
                    "pr": {
                        "id": 123,
                        "title": "",
                        "author": "",
                        "reviewers": [],
                        "status": ""
                    },
                    "action": ""
                }
            ])
        
        elif template_type == "jira":
            cases.extend([
                # Completely empty
                {},
                # Null ticket
                {"ticket": None, "change_type": "status_change"},
                # Empty ticket
                {"ticket": {}, "change_type": "status_change"},
                # Null values in ticket
                {
                    "ticket": {
                        "key": None,
                        "summary": None,
                        "assignee": None,
                        "priority": None,
                        "status": None
                    },
                    "change_type": None
                },
                # Empty strings in ticket
                {
                    "ticket": {
                        "key": "",
                        "summary": "",
                        "assignee": "",
                        "priority": "",
                        "status": ""
                    },
                    "change_type": ""
                }
            ])
        
        elif template_type == "alert":
            cases.extend([
                # Completely empty
                {},
                # Null alert
                {"alert": None},
                # Empty alert
                {"alert": {}},
                # Null values in alert
                {
                    "alert": {
                        "id": None,
                        "type": None,
                        "severity": None,
                        "title": None,
                        "description": None,
                        "affected_systems": None
                    }
                },
                # Empty strings in alert
                {
                    "alert": {
                        "id": "",
                        "type": "",
                        "severity": "",
                        "title": "",
                        "description": "",
                        "affected_systems": []
                    }
                }
            ])
        
        return cases
    
    def generate_malformed_data_cases(self, template_type: str) -> List[Dict[str, Any]]:
        """Generate test cases with malformed data types."""
        cases = []
        
        if template_type == "standup":
            cases.extend([
                # Wrong data types
                {
                    "date": 20250814,  # Should be string
                    "team": ["not", "a", "string"],  # Should be string
                    "team_members": "not a list",  # Should be list
                    "stats": "not a dict",  # Should be dict
                    "action_items": {"not": "a list"}  # Should be list
                },
                # Nested wrong types
                {
                    "date": "2025-08-14",
                    "team": "Test Team",
                    "team_members": [
                        {
                            "name": 12345,  # Should be string
                            "yesterday": "not a list",  # Should be list
                            "today": {"not": "a list"},  # Should be list
                            "blockers": 42  # Should be list
                        }
                    ],
                    "stats": [1, 2, 3],  # Should be dict
                    "action_items": "not a list"  # Should be list
                }
            ])
        
        elif template_type == "pr":
            cases.extend([
                # Wrong data types
                {
                    "pr": "not a dict",  # Should be dict
                    "action": 123  # Should be string
                },
                # Nested wrong types
                {
                    "pr": {
                        "id": "not a number",  # Should be int
                        "title": 12345,  # Should be string
                        "reviewers": "not a list",  # Should be list
                        "files_changed": "not a number",  # Should be int
                        "draft": "not a boolean"  # Should be boolean
                    },
                    "action": ["not", "a", "string"]  # Should be string
                }
            ])
        
        elif template_type == "jira":
            cases.extend([
                # Wrong data types
                {
                    "ticket": "not a dict",  # Should be dict
                    "change_type": 123  # Should be string
                },
                # Nested wrong types
                {
                    "ticket": {
                        "key": 12345,  # Should be string
                        "story_points": "not a number",  # Should be int
                        "comments": "not a list",  # Should be list
                        "created": 20250814  # Should be string
                    },
                    "change_type": ["not", "a", "string"]  # Should be string
                }
            ])
        
        elif template_type == "alert":
            cases.extend([
                # Wrong data types
                {
                    "alert": "not a dict"  # Should be dict
                },
                # Nested wrong types
                {
                    "alert": {
                        "id": 12345,  # Should be string
                        "severity": ["not", "a", "string"],  # Should be string
                        "affected_systems": "not a list",  # Should be list
                        "created_at": 20250814  # Should be string
                    }
                }
            ])
        
        return cases
    
    def generate_boundary_value_cases(self, template_type: str) -> List[Dict[str, Any]]:
        """Generate test cases with boundary values."""
        cases = []
        
        if template_type == "standup":
            cases.extend([
                # Very large team
                {
                    "date": "2025-08-14",
                    "team": "Boundary Test Team",
                    "team_members": [
                        {
                            "name": f"User{i:05d}",
                            "yesterday": [f"Task{j}" for j in range(100)],  # Many tasks
                            "today": [f"Task{j}" for j in range(100)],
                            "blockers": [f"Blocker{j}" for j in range(50)]
                        }
                        for i in range(1000)  # Very large team
                    ],
                    "stats": {
                        "prs_merged": 999999,
                        "prs_open": 999999,
                        "tickets_completed": 999999,
                        "commits": 999999
                    }
                },
                # Single member team
                {
                    "date": "2025-08-14",
                    "team": "Solo Team",
                    "team_members": [
                        {
                            "name": "Solo Developer",
                            "yesterday": [],
                            "today": [],
                            "blockers": []
                        }
                    ],
                    "stats": {
                        "prs_merged": 0,
                        "prs_open": 0,
                        "tickets_completed": 0,
                        "commits": 0
                    }
                }
            ])
        
        elif template_type == "pr":
            cases.extend([
                # Massive PR
                {
                    "pr": {
                        "id": 999999,
                        "title": "X" * 1000,  # Very long title
                        "description": "X" * 10000,  # Very long description
                        "author": "boundary_test_user",
                        "reviewers": [f"reviewer{i}" for i in range(100)],  # Many reviewers
                        "files_changed": 10000,
                        "additions": 1000000,
                        "deletions": 500000
                    },
                    "action": "opened"
                },
                # Minimal PR
                {
                    "pr": {
                        "id": 1,
                        "title": "X",  # Single character
                        "description": "",
                        "author": "u",
                        "reviewers": [],
                        "files_changed": 1,
                        "additions": 1,
                        "deletions": 0
                    },
                    "action": "opened"
                }
            ])
        
        elif template_type == "jira":
            cases.extend([
                # Ticket with massive data
                {
                    "ticket": {
                        "key": "BOUNDARY-999999",
                        "summary": "X" * 1000,
                        "description": "X" * 50000,
                        "story_points": 999,
                        "comments": [
                            {
                                "author": f"user{i}",
                                "text": "X" * 5000,
                                "created": "2025-08-14T10:00:00Z"
                            }
                            for i in range(1000)  # Many comments
                        ]
                    },
                    "change_type": "comment_added"
                },
                # Minimal ticket
                {
                    "ticket": {
                        "key": "B-1",
                        "summary": "X",
                        "description": "",
                        "story_points": 1,
                        "comments": []
                    },
                    "change_type": "status_change"
                }
            ])
        
        elif template_type == "alert":
            cases.extend([
                # Massive alert
                {
                    "alert": {
                        "id": "BOUNDARY-ALERT-999999",
                        "type": "service_outage",
                        "severity": "critical",
                        "title": "X" * 1000,
                        "description": "X" * 50000,
                        "affected_systems": [f"system{i}.com" for i in range(1000)],
                        "escalation_contacts": [f"user{i}@company.com" for i in range(100)],
                        "resolution_steps": [f"Step {i}: " + "X" * 500 for i in range(100)]
                    }
                },
                # Minimal alert
                {
                    "alert": {
                        "id": "B-1",
                        "type": "info",
                        "severity": "low",
                        "title": "X",
                        "description": "",
                        "affected_systems": [],
                        "escalation_contacts": [],
                        "resolution_steps": []
                    }
                }
            ])
        
        return cases
    
    def generate_unicode_and_special_character_cases(self, template_type: str) -> List[Dict[str, Any]]:
        """Generate test cases with unicode and special characters."""
        unicode_strings = [
            "🚀 Rocket Ship",
            "αβγδεζηθικλμνξοπρστυφχψω",  # Greek
            "こんにちは世界",  # Japanese
            "مرحبا بالعالم",  # Arabic
            "🎉🎊🎈🎁🎂🍰",  # Emojis
            "\\n\\t\\r\\\"\\'\\/",  # Escape sequences
            "<script>alert('xss')</script>",  # HTML/JS
            "SELECT * FROM users; DROP TABLE users;",  # SQL injection
            "../../etc/passwd",  # Path traversal
            "\x00\x01\x02\x03",  # Control characters
        ]
        
        cases = []
        
        for unicode_str in unicode_strings:
            if template_type == "standup":
                cases.append({
                    "date": "2025-08-14",
                    "team": unicode_str,
                    "team_members": [
                        {
                            "name": unicode_str,
                            "yesterday": [unicode_str],
                            "today": [unicode_str],
                            "blockers": [unicode_str]
                        }
                    ]
                })
            
            elif template_type == "pr":
                cases.append({
                    "pr": {
                        "id": 123,
                        "title": unicode_str,
                        "description": unicode_str,
                        "author": unicode_str
                    },
                    "action": "opened"
                })
            
            elif template_type == "jira":
                cases.append({
                    "ticket": {
                        "key": "TEST-123",
                        "summary": unicode_str,
                        "description": unicode_str,
                        "assignee": unicode_str
                    },
                    "change_type": "status_change"
                })
            
            elif template_type == "alert":
                cases.append({
                    "alert": {
                        "id": "ALERT-123",
                        "type": "service_outage",
                        "severity": "high",
                        "title": unicode_str,
                        "description": unicode_str
                    }
                })
        
        return cases
    
    def generate_date_and_time_edge_cases(self, template_type: str) -> List[Dict[str, Any]]:
        """Generate test cases with problematic date/time values."""
        problematic_dates = [
            "invalid-date",
            "2025-13-45",  # Invalid month/day
            "2025-02-30",  # Invalid date for February
            "2025-08-14T25:70:90Z",  # Invalid time
            "",  # Empty date
            "0000-00-00",
            "9999-12-31T23:59:59Z",  # Far future
            "1900-01-01T00:00:00Z",  # Far past
            "2025-08-14",  # No time
            "T10:00:00Z",  # No date
            "2025/08/14",  # Wrong format
            "Aug 14, 2025",  # Wrong format
            "1692014400",  # Unix timestamp
            None,  # Null date
        ]
        
        cases = []
        
        for date_str in problematic_dates:
            if template_type == "standup":
                cases.append({
                    "date": date_str,
                    "team": "Date Test Team",
                    "team_members": []
                })
            
            elif template_type == "pr":
                cases.append({
                    "pr": {
                        "id": 123,
                        "title": "Date Test PR",
                        "created_at": date_str,
                        "updated_at": date_str
                    },
                    "action": "opened"
                })
            
            elif template_type == "jira":
                cases.append({
                    "ticket": {
                        "key": "DATE-123",
                        "summary": "Date Test Ticket",
                        "created": date_str,
                        "updated": date_str
                    },
                    "change_type": "status_change"
                })
            
            elif template_type == "alert":
                cases.append({
                    "alert": {
                        "id": "DATE-ALERT-123",
                        "type": "service_outage",
                        "severity": "high",
                        "title": "Date Test Alert",
                        "created_at": date_str
                    }
                })
        
        return cases
    
    def generate_circular_reference_cases(self, template_type: str) -> List[Dict[str, Any]]:
        """Generate test cases with circular references (where possible)."""
        cases = []
        
        # Create objects with circular references (but avoid infinite recursion in JSON)
        if template_type == "standup":
            # Simulate circular reference with string reference instead
            cases.append({
                "date": "2025-08-14",
                "team": "Circular Team",
                "team_members": [
                    {
                        "name": "Circular User",
                        "yesterday": [],
                        "today": [],
                        "blockers": [],
                        "self_reference": "CIRCULAR_REF_TO_SELF"  # String instead of actual reference
                    }
                ]
            })
        
        elif template_type == "jira":
            # Simulate circular reference with string reference
            cases.append({
                "ticket": {
                    "key": "CIRCULAR-123",
                    "summary": "Circular Ticket",
                    "linked_issues": ["CIRCULAR-123"]  # Self-reference by key
                },
                "change_type": "status_change"
            })
        
        return cases
    
    def generate_deeply_nested_cases(self, template_type: str) -> List[Dict[str, Any]]:
        """Generate test cases with deeply nested structures."""
        def create_deep_nesting(depth: int, current: int = 0) -> Dict[str, Any]:
            if current >= depth:
                return {"value": f"depth_{current}"}
            return {"nested": create_deep_nesting(depth, current + 1)}
        
        cases = []
        
        if template_type == "standup":
            cases.append({
                "date": "2025-08-14",
                "team": "Deep Nesting Team",
                "team_members": [
                    {
                        "name": "Deep User",
                        "metadata": create_deep_nesting(50),  # 50 levels deep
                        "yesterday": [],
                        "today": [],
                        "blockers": []
                    }
                ]
            })
        
        elif template_type == "alert":
            cases.append({
                "alert": {
                    "id": "DEEP-ALERT-123",
                    "type": "service_outage",
                    "severity": "high",
                    "title": "Deep Nesting Alert",
                    "metadata": create_deep_nesting(50)  # 50 levels deep
                }
            })
        
        return cases
    
    def generate_all_edge_cases(self, template_type: str) -> Dict[str, List[Dict[str, Any]]]:
        """Generate all edge case categories for a template type."""
        return {
            "null_and_empty": self.generate_null_and_empty_cases(template_type),
            "malformed_data": self.generate_malformed_data_cases(template_type),
            "boundary_values": self.generate_boundary_value_cases(template_type),
            "unicode_special_chars": self.generate_unicode_and_special_character_cases(template_type),
            "date_time_issues": self.generate_date_and_time_edge_cases(template_type),
            "circular_references": self.generate_circular_reference_cases(template_type),
            "deep_nesting": self.generate_deeply_nested_cases(template_type)
        }


def generate_comprehensive_edge_cases() -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """Generate comprehensive edge cases for all template types."""
    generator = EdgeCaseDataGenerator()
    template_types = ["standup", "pr", "jira", "alert"]
    
    all_edge_cases = {}
    
    for template_type in template_types:
        all_edge_cases[template_type] = generator.generate_all_edge_cases(template_type)
    
    return all_edge_cases


def save_edge_cases_to_file(filename: str = "edge_cases_test_data.json"):
    """Save edge cases to a JSON file for external testing."""
    edge_cases = generate_comprehensive_edge_cases()
    
    # Convert to JSON-serializable format (handle circular references)
    def json_serializable(obj):
        if isinstance(obj, dict):
            return {k: json_serializable(v) for k, v in obj.items() if k != "self_reference"}
        elif isinstance(obj, list):
            return [json_serializable(item) for item in obj]
        else:
            return obj
    
    serializable_cases = json_serializable(edge_cases)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(serializable_cases, f, indent=2, ensure_ascii=False)
    
    return filename


if __name__ == "__main__":
    print("Testing edge case data generators...")
    
    generator = EdgeCaseDataGenerator()
    template_types = ["standup", "pr", "jira", "alert"]
    
    total_cases = 0
    
    for template_type in template_types:
        try:
            edge_cases = generator.generate_all_edge_cases(template_type)
            
            type_total = sum(len(cases) for cases in edge_cases.values())
            total_cases += type_total
            
            print(f"✅ {template_type.upper()} edge cases: {type_total} cases across {len(edge_cases)} categories")
            
            # Test each category
            for category, cases in edge_cases.items():
                assert isinstance(cases, list)
                assert len(cases) > 0
                print(f"   - {category}: {len(cases)} cases")
            
        except Exception as e:
            print(f"❌ {template_type.upper()} edge cases failed: {e}")
    
    print(f"\n✅ Total edge cases generated: {total_cases}")
    
    # Test comprehensive generation
    try:
        all_edge_cases = generate_comprehensive_edge_cases()
        comprehensive_total = sum(
            sum(len(cases) for cases in template_cases.values())
            for template_cases in all_edge_cases.values()
        )
        print(f"✅ Comprehensive edge cases: {comprehensive_total} total cases")
        
        # Test JSON serialization
        filename = save_edge_cases_to_file("test_edge_cases.json")
        print(f"✅ Edge cases saved to: {filename}")
        
    except Exception as e:
        print(f"❌ Comprehensive edge case generation failed: {e}")
    
    print("Edge case data generator testing completed!")