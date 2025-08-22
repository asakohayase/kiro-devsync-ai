# MessageBatcher Enhancement Implementation Plan

- [x] 1. Fix existing implementation inconsistencies
  - Remove all references to the non-existent `_batch_groups` attribute
  - Ensure all methods consistently use `_channel_batch_groups` for batch storage
  - Fix statistics calculations to work with channel-specific data structures
  - Update `get_batch_stats()` method to accurately reflect current state
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 2. Enhance BatchGroup class with channel awareness
  - [x] 2.1 Add channel_id field to BatchGroup dataclass
    - Add `channel_id: str` field to associate batches with specific channels
    - Add `last_activity: datetime` field to track recent batch activity
    - Update `should_flush()` method to use configurable max_size parameter (default 5)
    - Create unit tests for enhanced BatchGroup functionality
    - _Requirements: 2.1, 2.2, 3.1, 3.2_

  - [x] 2.2 Implement ChannelStats dataclass for per-channel analytics
    - Create ChannelStats dataclass with comprehensive channel metrics
    - Add fields for batches_created, batches_sent, messages_batched, averages
    - Implement methods to update statistics when batches are processed
    - Write unit tests for ChannelStats calculations and updates
    - _Requirements: 6.1, 6.2, 6.3_

- [x] 3. Fix and enhance core batching methods
  - [x] 3.1 Fix _find_or_create_batch_group method for channel support
    - Update method signature to accept channel_id parameter
    - Modify group key generation to include channel context
    - Ensure batch groups are stored in correct channel-specific dictionary
    - Update similarity detection to work within channel boundaries
    - Write tests for channel-aware batch group creation and retrieval
    - _Requirements: 1.1, 1.2, 2.1, 2.2_

  - [x] 3.2 Fix _flush_batch_group method with proper cleanup
    - Update method to remove batches from correct channel-specific storage
    - Add proper error handling for batch removal and cleanup
    - Update statistics tracking for both channel and global metrics
    - Implement memory cleanup to prevent resource leaks
    - Write tests for batch flushing and resource cleanup
    - _Requirements: 3.1, 3.2, 7.4_

- [x] 4. Implement SlackMessageFormatterFactory integration
  - [x] 4.1 Add proper formatter factory initialization and usage
    - Store formatter_factory reference in constructor if provided
    - Create BatchFormatterContext dataclass for formatter integration
    - Update _create_batched_message to use formatter factory when available
    - Implement fallback formatting when formatter factory is not available
    - Write unit tests for formatter integration and fallback scenarios
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 4.2 Enhance batch message creation with formatter integration
    - Modify _create_batched_message to use SlackMessageFormatterFactory
    - Create proper message type routing for different batch content types
    - Implement consistent formatting across different message types within batches
    - Add comprehensive fallback text generation for accessibility
    - Write integration tests for formatter factory usage in batch messages
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 5. Implement comprehensive analytics and monitoring
  - [x] 5.1 Create enhanced statistics tracking system
    - Implement _channel_stats dictionary to track per-channel metrics
    - Add _global_stats tracking for system-wide batch analytics
    - Update all batch operations to properly update statistics
    - Create get_channel_stats method for channel-specific analytics
    - Write unit tests for statistics accuracy and consistency
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 5.2 Add health monitoring and performance metrics
    - Implement get_health_status method with system health indicators
    - Add performance metrics tracking (throughput, latency, memory usage)
    - Create alerting logic for stuck batches and resource issues
    - Implement automatic cleanup triggers based on health metrics
    - Write tests for health monitoring and performance tracking
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 6. Add manual control and inspection methods
  - [x] 6.1 Implement batch inspection methods
    - Create inspect_pending_batches method to view batches without sending
    - Add force_flush_batch method to manually send specific batches
    - Implement batch filtering and search capabilities for inspection
    - Add detailed batch information including timing and content summaries
    - Write unit tests for inspection methods and manual controls
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 6.2 Add resource management and cleanup methods
    - Implement cleanup_stale_batches method for automatic maintenance
    - Add memory pressure detection and automatic batch flushing
    - Create graceful shutdown method to flush all pending batches
    - Implement channel cleanup for inactive channels
    - Write tests for resource management and cleanup functionality
    - _Requirements: 5.1, 5.2, 7.4_

- [x] 7. Enhance configuration and error handling
  - [x] 7.1 Update BatchConfig with new configuration options
    - Add max_channels, cleanup_interval_minutes, health_check_interval_minutes
    - Set max_batch_size default to 5 (changed from 10)
    - Add enable_formatter_integration and fallback_formatting options
    - Create configuration validation and default value handling
    - Write unit tests for configuration validation and defaults
    - _Requirements: 3.1, 3.2, 4.4, 6.4_

  - [x] 7.2 Implement comprehensive error handling
    - Create BatchErrorHandler class for centralized error management
    - Add graceful fallback formatting when SlackMessageFormatterFactory fails
    - Implement channel overflow handling and automatic cleanup
    - Add memory pressure handling with proactive batch flushing
    - Write unit tests for all error scenarios and recovery mechanisms
    - _Requirements: 4.4, 7.1, 7.2, 7.3, 7.4_

- [x] 8. Add comprehensive testing and validation
  - [x] 8.1 Create unit tests for all enhanced functionality
    - Write tests for channel-specific batch management
    - Test time-based and size-based batch flushing logic
    - Validate statistics accuracy across all operations
    - Test error handling and recovery mechanisms
    - Create performance tests for high-volume scenarios
    - _Requirements: All requirements validation_

  - [x] 8.2 Add integration tests for end-to-end functionality
    - Test complete message flow from add_message to batch delivery
    - Validate multi-channel concurrent batching scenarios
    - Test SlackMessageFormatterFactory integration in realistic scenarios
    - Verify resource cleanup and memory management under load
    - Create stress tests for system limits and edge cases
    - _Requirements: All requirements validation_

- [x] 9. Update documentation and examples
  - [x] 9.1 Update MessageBatcher class documentation
    - Document all new methods and enhanced functionality
    - Add usage examples for channel-specific batching
    - Document SlackMessageFormatterFactory integration patterns
    - Create troubleshooting guide for common issues
    - Add performance tuning recommendations
    - _Requirements: Documentation and usability_

  - [x] 9.2 Create migration guide for existing users
    - Document changes from existing implementation
    - Provide migration examples for common use cases
    - Explain new configuration options and their impact
    - Create backward compatibility notes and recommendations
    - Add FAQ for common migration questions
    - _Requirements: Migration and adoption support_