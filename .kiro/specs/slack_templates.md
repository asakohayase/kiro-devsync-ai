# Slack Message Templates Specification

## Overview
Create Slack Block Kit message templates for DevSync AI notifications.

## Requirements

### Template Functions
Create functions that return properly formatted Slack blocks for:

1. **GitHub PR Notifications**
   - `create_pr_notification(pr_data)` - New PR created
   - `create_pr_merged_notification(pr_data)` - PR merged
   - `create_pr_conflict_notification(pr_data)` - PR has conflicts
   - Include emojis: 🔀 (new PR), ✅ (merged), ⚠️ (conflicts)

2. **Status Updates**
   - `create_daily_summary(summary_data)` - Daily team summary
   - `create_blocker_alert(blocker_data)` - Team blocker detected
   - `create_activity_update(activity_data)` - General activity update

3. **System Messages**
   - `create_error_notification(error_data)` - System errors
   - `create_success_notification(message)` - Success confirmations

### Block Kit Requirements
- Use proper Slack Block Kit JSON structure
- Include interactive elements where appropriate (buttons, links)
- Rich formatting with emojis and proper styling
- Fallback text for accessibility
- Action buttons for common operations (view PR, assign reviewer)

### Data Structure
Each template function should accept a dictionary with relevant data:
- PR data: title, author, url, branch, reviewers, status
- Summary data: pr_count, active_developers, completion_rate
- Error data: error_type, message, timestamp, severity

### Styling Guidelines
- Use consistent emoji scheme across templates
- Include severity indicators (🟢 good, 🟡 warning, 🔴 critical)
- Format code elements with backticks
- Include relevant action buttons and links