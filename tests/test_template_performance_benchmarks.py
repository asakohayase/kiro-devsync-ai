"""
Performance benchmarking tests for template rendering.
Tests template rendering performance, memory usage, and scalability.
"""

import pytest
import time
import gc
import sys
from typing import Dict, List, Any
from unittest.mock import patch

from devsync_ai.templates.standup_template import StandupTemplate
from devsync_ai.templates.pr_templates import NewPRTemplate
from devsync_ai.templates.jira_templates import JIRATemplate
from devsync_ai.templates.alert_templates import AlertTemplate
from devsync_ai.core.message_formatter import TemplateConfig, SlackMessage


class TestTemplatePerformanceBenchmarks:
    """Performance benchmarking tests for template rendering."""
    
    def test_single_template_rendering_benchmark(self):
        """Benchmark single template rendering performance."""
        template = StandupTemplate()
        data = {
            'date': '2025-08-14',
            'team': 'Benchmark Team',
            'team_members': [
                {'name': f'User {i}', 'yesterday': [f'Task {i}'], 'today': [f'Task {i+1}'], 'blockers': []}
                for i in range(10)  # 10 team members
            ]
        }
        
        # Warm up
        for _ in range(5):
            template.format_message(data)
        
        # Benchmark
        iterations = 100
        start_time = time.time()
        
        for _ in range(iterations):
            message = template.format_message(data)
            assert isinstance(message, SlackMessage)
        
        total_time = time.time() - start_time
        avg_time = total_time / iterations
        
        print(f"Single template rendering: {avg_time*1000:.2f}ms per message")
        
        # Performance assertions
        assert avg_time < 0.1  # Less than 100ms per message
        assert total_time < 10  # Less than 10 seconds total
    
    def test_multiple_template_types_benchmark(self):
        """Benchmark rendering performance across different template types."""
        templates_and_data = [
            (StandupTemplate(), {
                'date': '2025-08-14',
                'team': 'Test Team',
                'team_members': [
                    {'name': 'User 1', 'yesterday': [], 'today': [], 'blockers': []}
                ]
            }),
            (NewPRTemplate(), {
                'pr': {
                    'number': 123,
                    'title': 'Test PR',
                    'author': 'test.user'
                }
            }),
            (JIRATemplate(), {
                'ticket': {
                    'key': 'TEST-123',
                    'summary': 'Test ticket',
                    'status': 'In Progress'
                }
            }),
            (AlertTemplate(), {
                'alert': {
                    'title': 'Test Alert',
                    'severity': 'medium',
                    'description': 'Test description'
                }
            })
        ]
        
        results = {}
        
        for template, data in templates_and_data:
            template_name = template.__class__.__name__
            
            # Warm up
            for _ in range(3):
                template.format_message(data)
            
            # Benchmark
            iterations = 50
            start_time = time.time()
            
            for _ in range(iterations):
                message = template.format_message(data)
                assert isinstance(message, SlackMessage)
            
            total_time = time.time() - start_time
            avg_time = total_time / iterations
            results[template_name] = avg_time
            
            print(f"{template_name}: {avg_time*1000:.2f}ms per message")
            
            # Each template should render reasonably quickly
            assert avg_time < 0.2  # Less than 200ms per message
        
        # All templates should have similar performance characteristics
        max_time = max(results.values())
        min_time = min(results.values())
        assert max_time / min_time < 5  # No template should be 5x slower than others
    
    def test_large_data_set_performance(self):
        """Test performance with large data sets."""
        template = StandupTemplate()
        
        # Create large data set
        large_data = {
            'date': '2025-08-14',
            'team': 'Large Team',
            'team_members': [
                {
                    'name': f'User {i}',
                    'yesterday': [f'Task {j}' for j in range(5)],  # 5 tasks each
                    'today': [f'Task {j+5}' for j in range(5)],
                    'blockers': [f'Blocker {j}' for j in range(2)] if i % 3 == 0 else []
                }
                for i in range(50)  # 50 team members
            ],
            'action_items': [
                {
                    'description': f'Action item {i}',
                    'assignee': f'user{i}',
                    'due_date': '2025-08-15'
                }
                for i in range(20)  # 20 action items
            ]
        }
        
        # Benchmark large data rendering
        iterations = 10
        start_time = time.time()
        
        for _ in range(iterations):
            message = template.format_message(large_data)
            assert isinstance(message, SlackMessage)
            assert len(message.blocks) > 0
        
        total_time = time.time() - start_time
        avg_time = total_time / iterations
        
        print(f"Large data set rendering: {avg_time*1000:.2f}ms per message")
        
        # Should handle large data sets reasonably well
        assert avg_time < 1.0  # Less than 1 second per large message
    
    def test_memory_usage_benchmark(self):
        """Benchmark memory usage during template rendering."""
        import tracemalloc
        
        template = StandupTemplate()
        data = {
            'date': '2025-08-14',
            'team': 'Memory Test Team',
            'team_members': [
                {'name': f'User {i}', 'yesterday': [], 'today': [], 'blockers': []}
                for i in range(20)
            ]
        }
        
        # Start memory tracing
        tracemalloc.start()
        
        # Render multiple messages
        messages = []
        for i in range(100):
            message = template.format_message(data)
            messages.append(message)
        
        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        print(f"Memory usage: Current={current/1024/1024:.2f}MB, Peak={peak/1024/1024:.2f}MB")
        
        # Memory usage should be reasonable
        assert peak < 50 * 1024 * 1024  # Less than 50MB peak
        assert current < 30 * 1024 * 1024  # Less than 30MB current
        
        # Clean up
        del messages
        gc.collect()
    
    def test_template_creation_overhead(self):
        """Test template creation overhead vs reuse."""
        data = {
            'date': '2025-08-14',
            'team': 'Overhead Test Team',
            'team_members': []
        }
        
        # Test creating new template each time
        iterations = 50
        start_time = time.time()
        
        for _ in range(iterations):
            template = StandupTemplate()
            message = template.format_message(data)
            assert isinstance(message, SlackMessage)
        
        creation_time = time.time() - start_time
        
        # Test reusing single template
        template = StandupTemplate()
        start_time = time.time()
        
        for _ in range(iterations):
            message = template.format_message(data)
            assert isinstance(message, SlackMessage)
        
        reuse_time = time.time() - start_time
        
        print(f"Template creation overhead: {creation_time*1000:.2f}ms vs reuse: {reuse_time*1000:.2f}ms")
        
        # Reuse should be faster than creation
        assert reuse_time < creation_time
        
        # Both should be reasonably fast
        assert creation_time < 5.0  # Less than 5 seconds
        assert reuse_time < 2.0     # Less than 2 seconds
    
    def test_configuration_impact_on_performance(self):
        """Test impact of different configurations on performance."""
        data = {
            'date': '2025-08-14',
            'team': 'Config Test Team',
            'team_members': []
        }
        
        configs = [
            TemplateConfig(team_id="basic"),
            TemplateConfig(team_id="interactive", interactive_elements=True),
            TemplateConfig(team_id="accessible", accessibility_mode=True),
            TemplateConfig(
                team_id="branded",
                branding={"team_name": "Test Team", "logo_emoji": "🚀"}
            )
        ]
        
        results = {}
        
        for config in configs:
            template = StandupTemplate(config=config)
            
            # Benchmark
            iterations = 30
            start_time = time.time()
            
            for _ in range(iterations):
                message = template.format_message(data)
                assert isinstance(message, SlackMessage)
            
            total_time = time.time() - start_time
            avg_time = total_time / iterations
            results[config.team_id] = avg_time
            
            print(f"Config {config.team_id}: {avg_time*1000:.2f}ms per message")
        
        # All configurations should perform reasonably
        for config_name, avg_time in results.items():
            assert avg_time < 0.2  # Less than 200ms per message
        
        # Configuration overhead should be minimal
        max_time = max(results.values())
        min_time = min(results.values())
        assert max_time / min_time < 3  # No config should be 3x slower
    
    def test_error_handling_performance_impact(self):
        """Test performance impact of error handling."""
        template = StandupTemplate()
        
        # Valid data benchmark
        valid_data = {
            'date': '2025-08-14',
            'team': 'Valid Team',
            'team_members': []
        }
        
        iterations = 50
        start_time = time.time()
        
        for _ in range(iterations):
            message = template.format_message(valid_data)
            assert isinstance(message, SlackMessage)
        
        valid_time = time.time() - start_time
        
        # Invalid data benchmark (triggers error handling)
        invalid_data = {}  # Missing required fields
        
        start_time = time.time()
        
        for _ in range(iterations):
            message = template.format_message(invalid_data)
            assert isinstance(message, SlackMessage)  # Should still return a message
        
        error_time = time.time() - start_time
        
        print(f"Valid data: {valid_time*1000:.2f}ms, Error handling: {error_time*1000:.2f}ms")
        
        # Error handling should not be significantly slower
        assert error_time < valid_time * 3  # At most 3x slower
        assert error_time < 5.0  # Less than 5 seconds total
    
    def test_concurrent_rendering_performance(self):
        """Test performance under concurrent rendering scenarios."""
        import threading
        import queue
        
        template = StandupTemplate()
        data = {
            'date': '2025-08-14',
            'team': 'Concurrent Team',
            'team_members': []
        }
        
        results = queue.Queue()
        
        def render_messages(thread_id, count):
            """Render messages in a thread."""
            start_time = time.time()
            
            for i in range(count):
                message = template.format_message(data)
                assert isinstance(message, SlackMessage)
            
            thread_time = time.time() - start_time
            results.put((thread_id, thread_time))
        
        # Create multiple threads
        thread_count = 5
        messages_per_thread = 20
        threads = []
        
        overall_start = time.time()
        
        for i in range(thread_count):
            thread = threading.Thread(target=render_messages, args=(i, messages_per_thread))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        overall_time = time.time() - overall_start
        
        # Collect results
        thread_times = []
        while not results.empty():
            thread_id, thread_time = results.get()
            thread_times.append(thread_time)
        
        avg_thread_time = sum(thread_times) / len(thread_times)
        
        print(f"Concurrent rendering: {overall_time*1000:.2f}ms overall, {avg_thread_time*1000:.2f}ms avg per thread")
        
        # Concurrent performance should be reasonable
        assert overall_time < 10.0  # Less than 10 seconds overall
        assert avg_thread_time < 5.0  # Less than 5 seconds per thread
        assert len(thread_times) == thread_count  # All threads completed


class TestTemplateScalabilityBenchmarks:
    """Test template system scalability under various loads."""
    
    def test_increasing_team_size_scalability(self):
        """Test scalability with increasing team sizes."""
        template = StandupTemplate()
        team_sizes = [1, 5, 10, 25, 50, 100]
        results = {}
        
        for team_size in team_sizes:
            data = {
                'date': '2025-08-14',
                'team': f'Team of {team_size}',
                'team_members': [
                    {'name': f'User {i}', 'yesterday': [], 'today': [], 'blockers': []}
                    for i in range(team_size)
                ]
            }
            
            # Benchmark
            iterations = 10
            start_time = time.time()
            
            for _ in range(iterations):
                message = template.format_message(data)
                assert isinstance(message, SlackMessage)
            
            total_time = time.time() - start_time
            avg_time = total_time / iterations
            results[team_size] = avg_time
            
            print(f"Team size {team_size}: {avg_time*1000:.2f}ms per message")
        
        # Performance should scale reasonably with team size
        for team_size, avg_time in results.items():
            # Larger teams should take more time, but not excessively
            expected_max_time = 0.01 * team_size + 0.1  # Linear scaling with reasonable base
            assert avg_time < expected_max_time
    
    def test_message_complexity_scalability(self):
        """Test scalability with increasing message complexity."""
        template = StandupTemplate()
        
        complexity_levels = [
            ('simple', {
                'date': '2025-08-14',
                'team': 'Simple Team',
                'team_members': []
            }),
            ('medium', {
                'date': '2025-08-14',
                'team': 'Medium Team',
                'team_members': [
                    {'name': 'User 1', 'yesterday': ['Task 1'], 'today': ['Task 2'], 'blockers': []}
                ],
                'stats': {'prs_opened': 5, 'prs_merged': 3}
            }),
            ('complex', {
                'date': '2025-08-14',
                'team': 'Complex Team',
                'team_members': [
                    {
                        'name': f'User {i}',
                        'yesterday': [f'Task {j}' for j in range(3)],
                        'today': [f'Task {j+3}' for j in range(3)],
                        'blockers': [f'Blocker {i}'] if i % 2 == 0 else []
                    }
                    for i in range(10)
                ],
                'action_items': [
                    {'description': f'Action {i}', 'assignee': f'user{i}'}
                    for i in range(5)
                ],
                'stats': {'prs_opened': 15, 'prs_merged': 10, 'tickets_completed': 20}
            })
        ]
        
        for complexity_name, data in complexity_levels:
            iterations = 20
            start_time = time.time()
            
            for _ in range(iterations):
                message = template.format_message(data)
                assert isinstance(message, SlackMessage)
            
            total_time = time.time() - start_time
            avg_time = total_time / iterations
            
            print(f"Complexity {complexity_name}: {avg_time*1000:.2f}ms per message")
            
            # Even complex messages should render reasonably quickly
            assert avg_time < 0.5  # Less than 500ms per message


if __name__ == "__main__":
    print("Running template performance benchmarks...")
    
    # Run a basic performance test
    template = StandupTemplate()
    data = {
        'date': '2025-08-14',
        'team': 'Benchmark Team',
        'team_members': []
    }
    
    # Warm up
    for _ in range(5):
        template.format_message(data)
    
    # Benchmark
    iterations = 50
    start_time = time.time()
    
    for _ in range(iterations):
        message = template.format_message(data)
        assert isinstance(message, SlackMessage)
    
    total_time = time.time() - start_time
    avg_time = total_time / iterations
    
    print(f"✅ Basic performance: {avg_time*1000:.2f}ms per message")
    assert avg_time < 0.1  # Should be fast
    
    print("Performance benchmarks completed!")