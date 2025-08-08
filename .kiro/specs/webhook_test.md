# GitHub Webhook Test Script Specification

## Overview
Create a test script that simulates GitHub webhook events to validate the agent hook works correctly.

## Requirements

### Test Data
Create realistic GitHub webhook payloads for:
1. PR opened event
2. PR merged event  
3. PR ready for review event
4. PR with conflicts event

### Test Functions
- `test_webhook_endpoint()` - Test basic connectivity
- `test_pr_opened()` - Test new PR notification
- `test_pr_merged()` - Test merged PR notification
- `test_error_handling()` - Test malformed payloads
- `simulate_github_webhook()` - Main test orchestrator

### HTTP Testing
- Use requests library to POST to webhook endpoint
- Include proper GitHub headers and signatures
- Test different payload formats
- Validate response codes and messages

### Integration Testing
- Start webhook server programmatically
- Send test payloads
- Verify Slack notifications are sent
- Clean shutdown after testing

## Output Requirements
- Clear test progress indicators
- Success/failure reporting for each test
- Performance metrics (response times)
- Integration validation results