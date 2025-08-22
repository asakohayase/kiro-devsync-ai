"""Tests for BatchConfig validation and default handling."""

import pytest
from devsync_ai.core.message_batcher import BatchConfig, BatchStrategy


class TestBatchConfig:
    """Test BatchConfig validation and functionality."""
    
    def test_default_config_creation(self):
        """Test creating default configuration."""
        config = BatchConfig()
        
        # Verify default values
        assert config.enabled is True
        assert config.max_batch_size == 5
        assert config.max_batch_age_minutes == 5
        assert config.similarity_threshold == 0.7
        assert config.enable_pagination is True
        assert config.items_per_page == 5
        assert config.enable_threading is True
        assert config.priority_ordering is True
        assert BatchStrategy.TIME_BASED in config.strategies
        assert BatchStrategy.CONTENT_SIMILARITY in config.strategies
        assert config.enable_formatter_integration is True
        assert config.fallback_formatting is True
        assert config.max_channels == 100
        assert config.cleanup_interval_minutes == 60
        assert config.health_check_interval_minutes == 5
        assert config.enable_analytics is True
        
        # Should be valid
        assert config.is_valid()
        assert len(config.validate()) == 0
    
    def test_create_default_factory_method(self):
        """Test create_default factory method."""
        config = BatchConfig.create_default()
        
        assert config.is_valid()
        assert config.max_batch_size == 5
        assert config.enable_formatter_integration is True
    
    def test_create_minimal_factory_method(self):
        """Test create_minimal factory method."""
        config = BatchConfig.create_minimal()
        
        assert config.is_valid()
        assert config.max_batch_size == 3
        assert config.max_batch_age_minutes == 2
        assert config.max_channels == 10
        assert config.enable_formatter_integration is False
        assert config.enable_analytics is False
    
    def test_validation_positive_values(self):
        """Test validation of positive value requirements."""
        # Test max_batch_size validation
        config = BatchConfig(max_batch_size=0)
        errors = config.validate()
        assert any("max_batch_size must be positive" in error for error in errors)
        assert not config.is_valid()
        
        # Test max_batch_age_minutes validation
        config = BatchConfig(max_batch_age_minutes=-1)
        errors = config.validate()
        assert any("max_batch_age_minutes must be positive" in error for error in errors)
        
        # Test items_per_page validation
        config = BatchConfig(items_per_page=0)
        errors = config.validate()
        assert any("items_per_page must be positive" in error for error in errors)
        
        # Test max_channels validation
        config = BatchConfig(max_channels=0)
        errors = config.validate()
        assert any("max_channels must be positive" in error for error in errors)
        
        # Test cleanup_interval_minutes validation
        config = BatchConfig(cleanup_interval_minutes=0)
        errors = config.validate()
        assert any("cleanup_interval_minutes must be positive" in error for error in errors)
        
        # Test health_check_interval_minutes validation
        config = BatchConfig(health_check_interval_minutes=0)
        errors = config.validate()
        assert any("health_check_interval_minutes must be positive" in error for error in errors)
    
    def test_validation_range_limits(self):
        """Test validation of range limits."""
        # Test similarity_threshold range
        config = BatchConfig(similarity_threshold=-0.1)
        errors = config.validate()
        assert any("similarity_threshold must be between 0.0 and 1.0" in error for error in errors)
        
        config = BatchConfig(similarity_threshold=1.1)
        errors = config.validate()
        assert any("similarity_threshold must be between 0.0 and 1.0" in error for error in errors)
        
        # Valid similarity threshold should pass
        config = BatchConfig(similarity_threshold=0.5)
        errors = config.validate()
        assert not any("similarity_threshold" in error for error in errors)
    
    def test_validation_performance_limits(self):
        """Test validation of performance-related limits."""
        # Test max_batch_size upper limit
        config = BatchConfig(max_batch_size=100)
        errors = config.validate()
        assert any("max_batch_size should not exceed 50" in error for error in errors)
        
        # Test max_batch_age_minutes upper limit
        config = BatchConfig(max_batch_age_minutes=120)
        errors = config.validate()
        assert any("max_batch_age_minutes should not exceed 60" in error for error in errors)
        
        # Test items_per_page upper limit
        config = BatchConfig(items_per_page=50)
        errors = config.validate()
        assert any("items_per_page should not exceed 20" in error for error in errors)
        
        # Test max_channels upper limit
        config = BatchConfig(max_channels=2000)
        errors = config.validate()
        assert any("max_channels should not exceed 1000" in error for error in errors)
    
    def test_validation_strategies_required(self):
        """Test validation requires at least one strategy."""
        config = BatchConfig(strategies=[])
        errors = config.validate()
        assert any("at least one batching strategy must be enabled" in error for error in errors)
        assert not config.is_valid()
    
    def test_to_dict_conversion(self):
        """Test converting configuration to dictionary."""
        config = BatchConfig(
            max_batch_size=3,
            similarity_threshold=0.8,
            strategies=[BatchStrategy.TIME_BASED]
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['max_batch_size'] == 3
        assert config_dict['similarity_threshold'] == 0.8
        assert config_dict['strategies'] == ['time_based']
        assert 'enabled' in config_dict
        assert 'enable_formatter_integration' in config_dict
    
    def test_from_dict_conversion(self):
        """Test creating configuration from dictionary."""
        config_data = {
            'enabled': True,
            'max_batch_size': 3,
            'max_batch_age_minutes': 2,
            'similarity_threshold': 0.8,
            'strategies': ['time_based', 'content_similarity'],
            'enable_formatter_integration': False,
            'max_channels': 50
        }
        
        config = BatchConfig.from_dict(config_data)
        
        assert config.enabled is True
        assert config.max_batch_size == 3
        assert config.max_batch_age_minutes == 2
        assert config.similarity_threshold == 0.8
        assert BatchStrategy.TIME_BASED in config.strategies
        assert BatchStrategy.CONTENT_SIMILARITY in config.strategies
        assert config.enable_formatter_integration is False
        assert config.max_channels == 50
    
    def test_from_dict_invalid_strategies(self):
        """Test handling invalid strategy names in from_dict."""
        config_data = {
            'strategies': ['time_based', 'invalid_strategy', 'content_similarity']
        }
        
        config = BatchConfig.from_dict(config_data)
        
        # Should only include valid strategies
        assert BatchStrategy.TIME_BASED in config.strategies
        assert BatchStrategy.CONTENT_SIMILARITY in config.strategies
        assert len(config.strategies) == 2
    
    def test_from_dict_empty_strategies(self):
        """Test handling empty strategies in from_dict."""
        config_data = {
            'strategies': []
        }
        
        config = BatchConfig.from_dict(config_data)
        
        # Should default to TIME_BASED when empty
        assert BatchStrategy.TIME_BASED in config.strategies
        assert len(config.strategies) == 1
    
    def test_validation_on_init(self):
        """Test that validation runs on initialization."""
        # This should not raise an exception but will log warnings
        config = BatchConfig(max_batch_size=-1)
        
        # Validation should have run and found errors
        errors = config.validate()
        assert len(errors) > 0
        assert not config.is_valid()
    
    def test_round_trip_dict_conversion(self):
        """Test that to_dict and from_dict are inverse operations."""
        original_config = BatchConfig(
            max_batch_size=7,
            similarity_threshold=0.9,
            strategies=[BatchStrategy.CONTENT_SIMILARITY],
            enable_formatter_integration=False,
            max_channels=25
        )
        
        # Convert to dict and back
        config_dict = original_config.to_dict()
        restored_config = BatchConfig.from_dict(config_dict)
        
        # Should be equivalent
        assert restored_config.max_batch_size == original_config.max_batch_size
        assert restored_config.similarity_threshold == original_config.similarity_threshold
        assert restored_config.strategies == original_config.strategies
        assert restored_config.enable_formatter_integration == original_config.enable_formatter_integration
        assert restored_config.max_channels == original_config.max_channels
    
    def test_config_immutability_after_validation(self):
        """Test that config can be modified after creation."""
        config = BatchConfig()
        
        # Should be able to modify values
        config.max_batch_size = 10
        assert config.max_batch_size == 10
        
        # Re-validation should work
        errors = config.validate()
        assert len(errors) == 0  # 10 is still valid
    
    def test_edge_case_values(self):
        """Test edge case values for configuration."""
        # Test minimum valid values
        config = BatchConfig(
            max_batch_size=1,
            max_batch_age_minutes=1,
            similarity_threshold=0.0,
            items_per_page=1,
            max_channels=1,
            cleanup_interval_minutes=1,
            health_check_interval_minutes=1
        )
        
        errors = config.validate()
        assert len(errors) == 0
        assert config.is_valid()
        
        # Test maximum valid values
        config = BatchConfig(
            max_batch_size=50,
            max_batch_age_minutes=60,
            similarity_threshold=1.0,
            items_per_page=20,
            max_channels=1000
        )
        
        errors = config.validate()
        assert len(errors) == 0
        assert config.is_valid()