#!/usr/bin/env python3
"""
Comprehensive webhook test script based on webhook_test.md specification.
Tests GitHub webhook functionality with realistic payloads and Slack integration.
"""

import json
import requests
import time
import hmac
import hashlib
import os
from datetime import datetime
from typing import Dict, Any, List
import unittest
from unittest.mock import patch, MagicMock

# Test configuration
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'http://localhost:8000/webhook')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'test-secret-key')
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', 'https://hooks.slack.com/test')

class GitHubWebhookTester:
    def __init__(self, webhook_url: str, secret: str):
        self.webhook_url = webhook_url
        self.secret = secret
        self.session = requests.Session()
        
    def generate_signature(self, payload: str) -> str:
        """Generate GitHub webhook signature"""
        signature = hmac.new(
            self.secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    def send_webhook(self, event_type: str, payload: Dict[Any, Any]) -> requests.Response:
        """Send webhook with proper headers and signature"""
        payload_str = json.dumps(payload)
        headers = {
            'Content-Type': 'application/json',
            'X-GitHub-Event': event_type,
            'X-GitHub-Delivery': f"test-delivery-{int(time.time())}",
            'X-Hub-Signature-256': self.generate_signature(payload_str),
            'User-Agent': 'GitHub-Hookshot/test'
        }
        
        return self.session.post(
            self.webhook_url,
            data=payload_str,
            headers=headers,
            timeout=30
        )

class WebhookPayloads:
    """Realistic GitHub webhook payloads for testing"""
    
    @staticmethod
    def push_payload() -> Dict[Any, Any]:
        return {
            "ref": "refs/heads/main",
            "before": "0000000000000000000000000000000000000000",
            "after": "1234567890abcdef1234567890abcdef12345678",
            "repository": {
                "id": 123456789,
                "name": "test-repo",
                "full_name": "testuser/test-repo",
                "owner": {
                    "name": "testuser",
                    "email": "test@example.com",
                    "login": "testuser",
                    "id": 12345,
                    "avatar_url": "https://github.com/images/error/testuser_happy.gif",
                    "type": "User"
                },
                "private": False,
                "html_url": "https://github.com/testuser/test-repo",
                "description": "Test repository for webhook testing",
                "fork": False,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-12-01T00:00:00Z",
                "pushed_at": "2023-12-01T12:00:00Z",
                "clone_url": "https://github.com/testuser/test-repo.git",
                "default_branch": "main"
            },
            "pusher": {
                "name": "testuser",
                "email": "test@example.com"
            },
            "sender": {
                "login": "testuser",
                "id": 12345,
                "avatar_url": "https://github.com/images/error/testuser_happy.gif",
                "type": "User"
            },
            "commits": [
                {
                    "id": "1234567890abcdef1234567890abcdef12345678",
                    "tree_id": "abcdef1234567890abcdef1234567890abcdef12",
                    "distinct": True,
                    "message": "Add new feature for webhook testing",
                    "timestamp": "2023-12-01T12:00:00Z",
                    "url": "https://github.com/testuser/test-repo/commit/1234567890abcdef1234567890abcdef12345678",
                    "author": {
                        "name": "Test User",
                        "email": "test@example.com",
                        "username": "testuser"
                    },
                    "committer": {
                        "name": "Test User",
                        "email": "test@example.com",
                        "username": "testuser"
                    },
                    "added": ["new_file.py"],
                    "removed": [],
                    "modified": ["README.md"]
                }
            ],
            "head_commit": {
                "id": "1234567890abcdef1234567890abcdef12345678",
                "tree_id": "abcdef1234567890abcdef1234567890abcdef12",
                "distinct": True,
                "message": "Add new feature for webhook testing",
                "timestamp": "2023-12-01T12:00:00Z",
                "url": "https://github.com/testuser/test-repo/commit/1234567890abcdef1234567890abcdef12345678",
                "author": {
                    "name": "Test User",
                    "email": "test@example.com",
                    "username": "testuser"
                },
                "committer": {
                    "name": "Test User",
                    "email": "test@example.com",
                    "username": "testuser"
                },
                "added": ["new_file.py"],
                "removed": [],
                "modified": ["README.md"]
            }
        }
    
    @staticmethod
    def pull_request_payload(action: str = "opened") -> Dict[Any, Any]:
        return {
            "action": action,
            "number": 42,
            "pull_request": {
                "id": 987654321,
                "number": 42,
                "state": "open",
                "locked": False,
                "title": "Add webhook testing functionality",
                "user": {
                    "login": "contributor",
                    "id": 54321,
                    "avatar_url": "https://github.com/images/error/contributor_happy.gif",
                    "type": "User"
                },
                "body": "This PR adds comprehensive webhook testing functionality including:\n- Realistic payload generation\n- Signature validation\n- Error handling\n- Slack integration testing",
                "created_at": "2023-12-01T10:00:00Z",
                "updated_at": "2023-12-01T11:00:00Z",
                "closed_at": None,
                "merged_at": None,
                "merge_commit_sha": None,
                "assignee": None,
                "assignees": [],
                "requested_reviewers": [],
                "requested_teams": [],
                "labels": [
                    {
                        "id": 111,
                        "name": "enhancement",
                        "color": "a2eeef",
                        "default": True
                    }
                ],
                "milestone": None,
                "draft": False,
                "commits_url": "https://api.github.com/repos/testuser/test-repo/pulls/42/commits",
                "review_comments_url": "https://api.github.com/repos/testuser/test-repo/pulls/42/comments",
                "review_comment_url": "https://api.github.com/repos/testuser/test-repo/pulls/comments{/number}",
                "comments_url": "https://api.github.com/repos/testuser/test-repo/issues/42/comments",
                "statuses_url": "https://api.github.com/repos/testuser/test-repo/statuses/abc123",
                "head": {
                    "label": "contributor:feature-branch",
                    "ref": "feature-branch",
                    "sha": "abc123def456abc123def456abc123def456abc1",
                    "user": {
                        "login": "contributor",
                        "id": 54321,
                        "type": "User"
                    },
                    "repo": {
                        "id": 123456789,
                        "name": "test-repo",
                        "full_name": "contributor/test-repo",
                        "owner": {
                            "login": "contributor",
                            "id": 54321,
                            "type": "User"
                        },
                        "private": False,
                        "html_url": "https://github.com/contributor/test-repo",
                        "clone_url": "https://github.com/contributor/test-repo.git",
                        "default_branch": "main"
                    }
                },
                "base": {
                    "label": "testuser:main",
                    "ref": "main",
                    "sha": "def456abc123def456abc123def456abc123def4",
                    "user": {
                        "login": "testuser",
                        "id": 12345,
                        "type": "User"
                    },
                    "repo": {
                        "id": 123456789,
                        "name": "test-repo",
                        "full_name": "testuser/test-repo",
                        "owner": {
                            "login": "testuser",
                            "id": 12345,
                            "type": "User"
                        },
                        "private": False,
                        "html_url": "https://github.com/testuser/test-repo",
                        "clone_url": "https://github.com/testuser/test-repo.git",
                        "default_branch": "main"
                    }
                },
                "merged": False,
                "mergeable": True,
                "rebaseable": True,
                "mergeable_state": "clean",
                "merged_by": None,
                "comments": 0,
                "review_comments": 0,
                "maintainer_can_modify": False,
                "commits": 3,
                "additions": 150,
                "deletions": 25,
                "changed_files": 5
            },
            "repository": {
                "id": 123456789,
                "name": "test-repo",
                "full_name": "testuser/test-repo",
                "owner": {
                    "login": "testuser",
                    "id": 12345,
                    "type": "User"
                },
                "private": False,
                "html_url": "https://github.com/testuser/test-repo",
                "description": "Test repository for webhook testing",
                "fork": False,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-12-01T00:00:00Z",
                "pushed_at": "2023-12-01T12:00:00Z",
                "clone_url": "https://github.com/testuser/test-repo.git",
                "default_branch": "main"
            },
            "sender": {
                "login": "contributor",
                "id": 54321,
                "avatar_url": "https://github.com/images/error/contributor_happy.gif",
                "type": "User"
            }
        }
    
    @staticmethod
    def issues_payload(action: str = "opened") -> Dict[Any, Any]:
        return {
            "action": action,
            "issue": {
                "id": 555666777,
                "number": 123,
                "title": "Bug in webhook processing",
                "user": {
                    "login": "bugfinder",
                    "id": 98765,
                    "avatar_url": "https://github.com/images/error/bugfinder_happy.gif",
                    "type": "User"
                },
                "labels": [
                    {
                        "id": 222,
                        "name": "bug",
                        "color": "d73a49",
                        "default": True
                    },
                    {
                        "id": 333,
                        "name": "priority-high",
                        "color": "ff0000",
                        "default": False
                    }
                ],
                "state": "open",
                "locked": False,
                "assignee": {
                    "login": "testuser",
                    "id": 12345,
                    "type": "User"
                },
                "assignees": [
                    {
                        "login": "testuser",
                        "id": 12345,
                        "type": "User"
                    }
                ],
                "milestone": {
                    "id": 444,
                    "number": 1,
                    "title": "v1.0.0",
                    "description": "First stable release",
                    "creator": {
                        "login": "testuser",
                        "id": 12345,
                        "type": "User"
                    },
                    "open_issues": 5,
                    "closed_issues": 15,
                    "state": "open",
                    "created_at": "2023-11-01T00:00:00Z",
                    "updated_at": "2023-12-01T00:00:00Z",
                    "due_on": "2024-01-01T00:00:00Z",
                    "closed_at": None
                },
                "comments": 2,
                "created_at": "2023-12-01T09:00:00Z",
                "updated_at": "2023-12-01T10:30:00Z",
                "closed_at": None,
                "body": "When processing webhooks with large payloads, the system occasionally times out. This needs investigation and fixing.\n\nSteps to reproduce:\n1. Send large webhook payload\n2. Monitor processing time\n3. Observe timeout after 30 seconds\n\nExpected: Processing should complete within timeout\nActual: System times out on large payloads"
            },
            "repository": {
                "id": 123456789,
                "name": "test-repo",
                "full_name": "testuser/test-repo",
                "owner": {
                    "login": "testuser",
                    "id": 12345,
                    "type": "User"
                },
                "private": False,
                "html_url": "https://github.com/testuser/test-repo",
                "description": "Test repository for webhook testing",
                "default_branch": "main"
            },
            "sender": {
                "login": "bugfinder",
                "id": 98765,
                "avatar_url": "https://github.com/images/error/bugfinder_happy.gif",
                "type": "User"
            }
        }
    
    @staticmethod
    def release_payload(action: str = "published") -> Dict[Any, Any]:
        return {
            "action": action,
            "release": {
                "id": 777888999,
                "tag_name": "v1.2.3",
                "target_commitish": "main",
                "name": "Version 1.2.3 - Webhook Improvements",
                "draft": False,
                "author": {
                    "login": "testuser",
                    "id": 12345,
                    "type": "User"
                },
                "prerelease": False,
                "created_at": "2023-12-01T14:00:00Z",
                "published_at": "2023-12-01T14:30:00Z",
                "assets": [
                    {
                        "id": 111222333,
                        "name": "webhook-tester-v1.2.3.tar.gz",
                        "label": "Source code (tar.gz)",
                        "uploader": {
                            "login": "testuser",
                            "id": 12345,
                            "type": "User"
                        },
                        "content_type": "application/gzip",
                        "state": "uploaded",
                        "size": 1024000,
                        "download_count": 0,
                        "created_at": "2023-12-01T14:15:00Z",
                        "updated_at": "2023-12-01T14:15:00Z",
                        "browser_download_url": "https://github.com/testuser/test-repo/releases/download/v1.2.3/webhook-tester-v1.2.3.tar.gz"
                    }
                ],
                "tarball_url": "https://api.github.com/repos/testuser/test-repo/tarball/v1.2.3",
                "zipball_url": "https://api.github.com/repos/testuser/test-repo/zipball/v1.2.3",
                "body": "## What's New\n\n- Enhanced webhook payload validation\n- Improved error handling and logging\n- Added comprehensive test suite\n- Better Slack integration\n\n## Bug Fixes\n\n- Fixed timeout issues with large payloads\n- Resolved signature validation edge cases\n- Improved memory usage for concurrent requests\n\n## Breaking Changes\n\nNone in this release.\n\n## Installation\n\n```bash\nwget https://github.com/testuser/test-repo/releases/download/v1.2.3/webhook-tester-v1.2.3.tar.gz\ntar -xzf webhook-tester-v1.2.3.tar.gz\n```"
            },
            "repository": {
                "id": 123456789,
                "name": "test-repo",
                "full_name": "testuser/test-repo",
                "owner": {
                    "login": "testuser",
                    "id": 12345,
                    "type": "User"
                },
                "private": False,
                "html_url": "https://github.com/testuser/test-repo",
                "description": "Test repository for webhook testing",
                "default_branch": "main"
            },
            "sender": {
                "login": "testuser",
                "id": 12345,
                "type": "User"
            }
        }

class WebhookTestSuite(unittest.TestCase):
    """Comprehensive webhook test suite"""
    
    def setUp(self):
        self.tester = GitHubWebhookTester(WEBHOOK_URL, WEBHOOK_SECRET)
        self.payloads = WebhookPayloads()
    
    def test_push_webhook_success(self):
        """Test successful push webhook processing"""
        payload = self.payloads.push_payload()
        response = self.tester.send_webhook('push', payload)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/json', response.headers.get('content-type', ''))
        
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'success')
        self.assertIn('message', response_data)
    
    def test_pull_request_opened_webhook(self):
        """Test pull request opened webhook"""
        payload = self.payloads.pull_request_payload('opened')
        response = self.tester.send_webhook('pull_request', payload)
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'success')
        self.assertIn('pull_request', response_data.get('processed_event', ''))
    
    def test_pull_request_closed_webhook(self):
        """Test pull request closed webhook"""
        payload = self.payloads.pull_request_payload('closed')
        response = self.tester.send_webhook('pull_request', payload)
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'success')
    
    def test_issues_webhook(self):
        """Test issues webhook processing"""
        payload = self.payloads.issues_payload('opened')
        response = self.tester.send_webhook('issues', payload)
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'success')
        self.assertIn('issue', response_data.get('processed_event', ''))
    
    def test_release_webhook(self):
        """Test release webhook processing"""
        payload = self.payloads.release_payload('published')
        response = self.tester.send_webhook('release', payload)
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'success')
        self.assertIn('release', response_data.get('processed_event', ''))
    
    def test_invalid_signature(self):
        """Test webhook with invalid signature"""
        payload = self.payloads.push_payload()
        payload_str = json.dumps(payload)
        
        headers = {
            'Content-Type': 'application/json',
            'X-GitHub-Event': 'push',
            'X-GitHub-Delivery': f"test-delivery-{int(time.time())}",
            'X-Hub-Signature-256': 'sha256=invalid_signature',
            'User-Agent': 'GitHub-Hookshot/test'
        }
        
        response = self.tester.session.post(
            self.tester.webhook_url,
            data=payload_str,
            headers=headers,
            timeout=30
        )
        
        self.assertEqual(response.status_code, 401)
        response_data = response.json()
        self.assertEqual(response_data.get('error'), 'Invalid signature')
    
    def test_missing_signature(self):
        """Test webhook without signature header"""
        payload = self.payloads.push_payload()
        payload_str = json.dumps(payload)
        
        headers = {
            'Content-Type': 'application/json',
            'X-GitHub-Event': 'push',
            'X-GitHub-Delivery': f"test-delivery-{int(time.time())}",
            'User-Agent': 'GitHub-Hookshot/test'
        }
        
        response = self.tester.session.post(
            self.tester.webhook_url,
            data=payload_str,
            headers=headers,
            timeout=30
        )
        
        self.assertEqual(response.status_code, 401)
        response_data = response.json()
        self.assertEqual(response_data.get('error'), 'Missing signature')
    
    def test_unsupported_event_type(self):
        """Test webhook with unsupported event type"""
        payload = {"test": "data"}
        response = self.tester.send_webhook('unsupported_event', payload)
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data.get('error'), 'Unsupported event type')
    
    def test_malformed_json(self):
        """Test webhook with malformed JSON payload"""
        malformed_payload = '{"invalid": json}'
        signature = hmac.new(
            self.tester.secret.encode('utf-8'),
            malformed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'Content-Type': 'application/json',
            'X-GitHub-Event': 'push',
            'X-GitHub-Delivery': f"test-delivery-{int(time.time())}",
            'X-Hub-Signature-256': f'sha256={signature}',
            'User-Agent': 'GitHub-Hookshot/test'
        }
        
        response = self.tester.session.post(
            self.tester.webhook_url,
            data=malformed_payload,
            headers=headers,
            timeout=30
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data.get('error'), 'Invalid JSON payload')
    
    def test_large_payload_handling(self):
        """Test webhook with large payload"""
        payload = self.payloads.push_payload()
        # Add large data to test payload size limits
        payload['large_data'] = 'x' * 1000000  # 1MB of data
        
        response = self.tester.send_webhook('push', payload)
        
        # Should either succeed or return appropriate error for payload too large
        self.assertIn(response.status_code, [200, 413])
        
        if response.status_code == 413:
            response_data = response.json()
            self.assertIn('payload too large', response_data.get('error', '').lower())
    
    def test_concurrent_webhooks(self):
        """Test handling of concurrent webhook requests"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def send_webhook_thread(event_type, payload):
            try:
                response = self.tester.send_webhook(event_type, payload)
                results.put(('success', response.status_code))
            except Exception as e:
                results.put(('error', str(e)))
        
        # Send multiple webhooks concurrently
        threads = []
        for i in range(5):
            payload = self.payloads.push_payload()
            payload['commits'][0]['id'] = f"commit{i}"
            thread = threading.Thread(target=send_webhook_thread, args=('push', payload))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=60)
        
        # Check results
        success_count = 0
        while not results.empty():
            result_type, result_value = results.get()
            if result_type == 'success' and result_value == 200:
                success_count += 1
        
        self.assertGreaterEqual(success_count, 3)  # At least 3 should succeed
    
    @patch('requests.post')
    def test_slack_notification_integration(self, mock_post):
        """Test Slack notification integration"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'ok': True}
        
        payload = self.payloads.push_payload()
        response = self.tester.send_webhook('push', payload)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify Slack webhook was called
        slack_calls = [call for call in mock_post.call_args_list 
                      if SLACK_WEBHOOK_URL in str(call)]
        self.assertGreater(len(slack_calls), 0)
        
        # Verify Slack message content
        slack_call = slack_calls[0]
        slack_payload = json.loads(slack_call[1]['data'])
        self.assertIn('text', slack_payload)
        self.assertIn('push', slack_payload['text'].lower())
    
    @patch('requests.post')
    def test_slack_notification_failure_handling(self, mock_post):
        """Test handling of Slack notification failures"""
        # Mock Slack webhook failure
        mock_slack_response = MagicMock()
        mock_slack_response.status_code = 500
        mock_slack_response.json.return_value = {'error': 'Internal server error'}
        
        # Mock main webhook success
        mock_webhook_response = MagicMock()
        mock_webhook_response.status_code = 200
        mock_webhook_response.json.return_value = {'status': 'success'}
        
        def side_effect(url, **kwargs):
            if SLACK_WEBHOOK_URL in url:
                return mock_slack_response
            else:
                return mock_webhook_response
        
        mock_post.side_effect = side_effect
        
        payload = self.payloads.push_payload()
        response = self.tester.send_webhook('push', payload)
        
        # Main webhook should still succeed even if Slack fails
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'success')
        # Should include warning about Slack notification failure
        self.assertIn('slack_notification_failed', response_data.get('warnings', []))
    
    def test_webhook_rate_limiting(self):
        """Test webhook rate limiting"""
        # Send multiple requests rapidly
        responses = []
        for i in range(10):
            payload = self.payloads.push_payload()
            payload['commits'][0]['id'] = f"rapid-commit-{i}"
            response = self.tester.send_webhook('push', payload)
            responses.append(response.status_code)
            time.sleep(0.1)  # Small delay between requests
        
        # Check if rate limiting is applied
        rate_limited = any(status == 429 for status in responses)
        successful = sum(1 for status in responses if status == 200)
        
        # Should have some successful requests
        self.assertGreater(successful, 0)
        
        # If rate limiting is implemented, some requests should be rate limited
        if rate_limited:
            self.assertLess(successful, 10)
    
    def test_webhook_timeout_handling(self):
        """Test webhook timeout handling"""
        # Create a payload that might cause processing delays
        payload = self.payloads.push_payload()
        payload['commits'] = [payload['commits'][0]] * 100  # Many commits
        
        start_time = time.time()
        try:
            response = self.tester.send_webhook('push', payload)
            processing_time = time.time() - start_time
            
            # Should complete within reasonable time
            self.assertLess(processing_time, 30)
            self.assertIn(response.status_code, [200, 408, 504])
            
        except requests.exceptions.Timeout:
            processing_time = time.time() - start_time
            self.assertLess(processing_time, 35)  # Should timeout before 35 seconds

def run_integration_tests():
    """Run integration tests with real webhook endpoint"""
    print("Starting webhook integration tests...")
    print(f"Testing webhook URL: {WEBHOOK_URL}")
    print(f"Using secret: {'*' * len(WEBHOOK_SECRET)}")
    print("-" * 60)
    
    # Test webhook endpoint availability
    try:
        response = requests.get(WEBHOOK_URL.replace('/webhook', '/health'), timeout=10)
        if response.status_code == 200:
            print("✓ Webhook endpoint is available")
        else:
            print(f"⚠ Webhook endpoint returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Webhook endpoint is not available: {e}")
        return False
    
    # Run test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(WebhookTestSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("-" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\nSuccess rate: {success_rate:.1f}%")
    
    return len(result.failures) == 0 and len(result.errors) == 0

def run_manual_tests():
    """Run manual tests with detailed output"""
    print("Running manual webhook tests...")
    print("-" * 60)
    
    tester = GitHubWebhookTester(WEBHOOK_URL, WEBHOOK_SECRET)
    payloads = WebhookPayloads()
    
    test_cases = [
        ('push', payloads.push_payload()),
        ('pull_request', payloads.pull_request_payload('opened')),
        ('pull_request', payloads.pull_request_payload('closed')),
        ('issues', payloads.issues_payload('opened')),
        ('issues', payloads.issues_payload('closed')),
        ('release', payloads.release_payload('published')),
    ]
    
    results = []
    
    for event_type, payload in test_cases:
        print(f"\nTesting {event_type} webhook...")
        try:
            start_time = time.time()
            response = tester.send_webhook(event_type, payload)
            processing_time = time.time() - start_time
            
            print(f"Status: {response.status_code}")
            print(f"Processing time: {processing_time:.3f}s")
            print(f"Response headers: {dict(response.headers)}")
            
            if response.headers.get('content-type', '').startswith('application/json'):
                response_data = response.json()
                print(f"Response body: {json.dumps(response_data, indent=2)}")
            else:
                print(f"Response body: {response.text[:200]}...")
            
            results.append({
                'event_type': event_type,
                'status_code': response.status_code,
                'processing_time': processing_time,
                'success': response.status_code == 200
            })
            
        except Exception as e:
            print(f"Error: {e}")
            results.append({
                'event_type': event_type,
                'status_code': None,
                'processing_time': None,
                'success': False,
                'error': str(e)
            })
    
    print("\n" + "=" * 60)
    print("MANUAL TEST SUMMARY")
    print("=" * 60)
    
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"Total tests: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Success rate: {successful/total*100:.1f}%")
    
    if successful < total:
        print("\nFailed tests:")
        for result in results:
            if not result['success']:
                error_msg = result.get('error', f"HTTP {result['status_code']}")
                print(f"- {result['event_type']}: {error_msg}")
    
    avg_time = sum(r['processing_time'] for r in results if r['processing_time']) / successful
    print(f"\nAverage processing time: {avg_time:.3f}s")
    
    return successful == total

if __name__ == "__main__":
    import sys
    
    print("GitHub Webhook Comprehensive Test Suite")
    print("=" * 60)
    print(f"Webhook URL: {WEBHOOK_URL}")
    print(f"Secret configured: {'Yes' if WEBHOOK_SECRET else 'No'}")
    print(f"Slack webhook configured: {'Yes' if SLACK_WEBHOOK_URL else 'No'}")
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--manual':
        success = run_manual_tests()
    else:
        success = run_integration_tests()
    
    sys.exit(0 if success else 1)
