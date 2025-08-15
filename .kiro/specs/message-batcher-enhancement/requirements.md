# MessageBatcher Enhancement Requirements

## Introduction

The existing MessageBatcher class in DevSync AI provides basic message batching functionality but has several implementation issues and missing features. This enhancement addresses the need for a robust, channel-aware message batching system that groups related notifications within time windows, maintains separate queues for different channels, and integrates properly with the SlackMessageFormatterFactory for optimal notification delivery.

## Requirements

### Requirement 1

**User Story:** As a DevSync AI system, I want to group related notifications within a 5-minute time window, so that users receive consolidated updates instead of notification spam.

#### Acceptance Criteria

1. WHEN multiple related notifications occur within 5 minutes THEN the system SHALL group them into a single batch message
2. WHEN the 5-minute time window expires THEN the system SHALL automatically send the batched message
3. WHEN notifications are of different types but related (same project/author) THEN the system SHALL still consider them for batching
4. WHEN a batch reaches the maximum size before the time limit THEN the system SHALL send it immediately

### Requirement 2

**User Story:** As a DevSync AI system, I want to maintain separate batch queues for different Slack channels, so that channel-specific batching doesn't interfere with each other.

#### Acceptance Criteria

1. WHEN notifications are destined for different channels THEN the system SHALL maintain separate batch queues for each channel
2. WHEN a channel has no activity THEN the system SHALL not create unnecessary batch queues for that channel
3. WHEN flushing batches THEN the system SHALL be able to flush all channels or specific channels independently
4. WHEN tracking statistics THEN the system SHALL provide per-channel batch analytics

### Requirement 3

**User Story:** As a DevSync AI system, I want batches to automatically send when they reach 5 items or the time limit expires, so that users receive timely updates without overwhelming frequency.

#### Acceptance Criteria

1. WHEN a batch reaches 5 items THEN the system SHALL immediately send the batch regardless of time remaining
2. WHEN a batch has been open for 5 minutes THEN the system SHALL send the batch regardless of item count
3. WHEN the system shuts down or restarts THEN the system SHALL flush all pending batches before termination
4. WHEN manual flushing is requested THEN the system SHALL provide methods to force-send batches

### Requirement 4

**User Story:** As a DevSync AI system, I want to integrate with the SlackMessageFormatterFactory for batch formatting, so that batched messages maintain consistent formatting and styling.

#### Acceptance Criteria

1. WHEN creating batched messages THEN the system SHALL use SlackMessageFormatterFactory for consistent formatting
2. WHEN different message types are batched together THEN the system SHALL format each type appropriately within the batch
3. WHEN batch messages are created THEN the system SHALL include proper fallback text for accessibility
4. WHEN formatting fails THEN the system SHALL provide graceful fallback formatting

### Requirement 5

**User Story:** As a DevSync AI administrator, I want methods to manually trigger batch sending, so that I can control notification timing during maintenance or testing.

#### Acceptance Criteria

1. WHEN manual flush is requested THEN the system SHALL provide a method to flush all pending batches immediately
2. WHEN channel-specific flush is needed THEN the system SHALL provide a method to flush batches for specific channels
3. WHEN expired batch cleanup is needed THEN the system SHALL provide a method to flush only expired batches
4. WHEN testing batch functionality THEN the system SHALL provide methods to inspect pending batches without sending them

### Requirement 6

**User Story:** As a DevSync AI administrator, I want batch analytics and monitoring capabilities, so that I can understand batching effectiveness and optimize notification patterns.

#### Acceptance Criteria

1. WHEN batch statistics are requested THEN the system SHALL provide metrics on batches created, sent, and pending
2. WHEN analyzing batch effectiveness THEN the system SHALL track average batch size, time-to-send, and channel activity
3. WHEN monitoring system health THEN the system SHALL provide alerts for stuck batches or excessive queue sizes
4. WHEN optimizing performance THEN the system SHALL provide insights into batching patterns and efficiency

### Requirement 7

**User Story:** As a DevSync AI system, I want to fix the existing implementation inconsistencies, so that the MessageBatcher works reliably across all use cases.

#### Acceptance Criteria

1. WHEN using channel-specific batching THEN the system SHALL consistently use the channel-aware data structures
2. WHEN tracking batch groups THEN the system SHALL not have conflicts between old single-batch and new channel-specific approaches
3. WHEN calculating statistics THEN the system SHALL accurately reflect the current state of all channel queues
4. WHEN cleaning up resources THEN the system SHALL properly manage memory and prevent resource leaks