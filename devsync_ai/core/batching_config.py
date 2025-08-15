"""Configuration management for smart message batching."""

import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

from .smart_message_batcher import SpamPreventionConfig, TimingConfig, TimingMode, SpamPreventionStrategy


@dataclass
class TeamBatchingConfig:
    """Team-specific batching configuration."""
    team_id: str
    spam_prevention: SpamPreventionConfig
    timing: TimingConfig
    channel_overrides: Dict[str, Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.channel_overrides is None:
            self.channel_overrides = {}


class BatchingConfigManager:
    """Manager for batching configuration loading and validation."""
    
    def __init__(self, config_dir: str = "config"):
        """Initialize configuration manager."""
        self.config_dir = Path(config_dir)
        self.logger = logging.getLogger(__name__)
        self._team_configs: Dict[str, TeamBatchingConfig] = {}
        self._default_config: Optional[TeamBatchingConfig] = None
    
    def load_team_config(self, team_id: str, config_file: Optional[str] = None) -> TeamBatchingConfig:
        """Load batching configuration for a specific team."""
        if team_id in self._team_configs:
            return self._team_configs[team_id]
        
        # Determine config file path
        if config_file:
            config_path = Path(config_file)
        else:
            config_path = self.config_dir / f"batching_config_{team_id}.yaml"
            if not config_path.exists():
                config_path = self.config_dir / "batching_config_default.yaml"
        
        try:
            config = self._load_config_from_file(config_path, team_id)
            self._team_configs[team_id] = config
            self.logger.info(f"Loaded batching config for team {team_id} from {config_path}")
            return config
        except Exception as e:
            self.logger.error(f"Failed to load batching config for team {team_id}: {e}")
            return self._get_default_config(team_id)
    
    def _load_config_from_file(self, config_path: Path, team_id: str) -> TeamBatchingConfig:
        """Load configuration from YAML file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Extract spam prevention config
        spam_data = config_data.get('spam_prevention', {})
        spam_config = SpamPreventionConfig(
            enabled=spam_data.get('enabled', True),
            max_messages_per_minute=spam_data.get('max_messages_per_minute', 10),
            max_messages_per_hour=spam_data.get('max_messages_per_hour', 100),
            burst_threshold=spam_data.get('burst_threshold', 5),
            burst_window_seconds=spam_data.get('burst_window_seconds', 30),
            cooldown_after_burst_minutes=spam_data.get('cooldown_after_burst_minutes', 5),
            duplicate_content_window_minutes=spam_data.get('duplicate_content_window_minutes', 15),
            priority_rate_limits=spam_data.get('priority_rate_limits', {
                'critical': 20, 'high': 15, 'medium': 10, 'low': 5, 'lowest': 2
            }),
            quiet_hours_start=spam_data.get('quiet_hours_start', 22),
            quiet_hours_end=spam_data.get('quiet_hours_end', 8),
            quiet_hours_enabled=spam_data.get('quiet_hours_enabled', True),
            strategies=[
                SpamPreventionStrategy(s) for s in spam_data.get('strategies', [
                    'rate_limiting', 'adaptive_timing', 'content_deduplication'
                ])
            ]
        )
        
        # Extract timing config
        timing_data = config_data.get('timing', {})
        timing_config = TimingConfig(
            mode=TimingMode(timing_data.get('mode', 'adaptive')),
            base_interval_minutes=timing_data.get('base_interval_minutes', 5),
            max_interval_minutes=timing_data.get('max_interval_minutes', 30),
            min_interval_minutes=timing_data.get('min_interval_minutes', 1),
            adaptive_factor=timing_data.get('adaptive_factor', 1.5),
            burst_detection_enabled=timing_data.get('burst_detection_enabled', True),
            user_activity_tracking=timing_data.get('user_activity_tracking', True),
            priority_timing_overrides=timing_data.get('priority_timing_overrides', {
                'critical': 0, 'high': 1, 'medium': 5, 'low': 15, 'lowest': 30
            })
        )
        
        # Extract channel overrides
        channel_overrides = config_data.get('channel_overrides', {})
        
        return TeamBatchingConfig(
            team_id=team_id,
            spam_prevention=spam_config,
            timing=timing_config,
            channel_overrides=channel_overrides
        )
    
    def _get_default_config(self, team_id: str) -> TeamBatchingConfig:
        """Get default configuration for a team."""
        if self._default_config is None:
            self._default_config = TeamBatchingConfig(
                team_id="default",
                spam_prevention=SpamPreventionConfig(),
                timing=TimingConfig()
            )
        
        # Create copy with team-specific ID
        return TeamBatchingConfig(
            team_id=team_id,
            spam_prevention=self._default_config.spam_prevention,
            timing=self._default_config.timing,
            channel_overrides={}
        )
    
    def save_team_config(self, config: TeamBatchingConfig, config_file: Optional[str] = None) -> bool:
        """Save team configuration to file."""
        try:
            # Determine config file path
            if config_file:
                config_path = Path(config_file)
            else:
                config_path = self.config_dir / f"batching_config_{config.team_id}.yaml"
            
            # Ensure directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to dictionary
            config_dict = self._config_to_dict(config)
            
            # Save to file
            with open(config_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            
            # Update cache
            self._team_configs[config.team_id] = config
            
            self.logger.info(f"Saved batching config for team {config.team_id} to {config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save batching config for team {config.team_id}: {e}")
            return False
    
    def _config_to_dict(self, config: TeamBatchingConfig) -> Dict[str, Any]:
        """Convert configuration to dictionary for YAML serialization."""
        return {
            'team_id': config.team_id,
            'spam_prevention': {
                'enabled': config.spam_prevention.enabled,
                'max_messages_per_minute': config.spam_prevention.max_messages_per_minute,
                'max_messages_per_hour': config.spam_prevention.max_messages_per_hour,
                'burst_threshold': config.spam_prevention.burst_threshold,
                'burst_window_seconds': config.spam_prevention.burst_window_seconds,
                'cooldown_after_burst_minutes': config.spam_prevention.cooldown_after_burst_minutes,
                'duplicate_content_window_minutes': config.spam_prevention.duplicate_content_window_minutes,
                'priority_rate_limits': config.spam_prevention.priority_rate_limits,
                'quiet_hours_start': config.spam_prevention.quiet_hours_start,
                'quiet_hours_end': config.spam_prevention.quiet_hours_end,
                'quiet_hours_enabled': config.spam_prevention.quiet_hours_enabled,
                'strategies': [s.value for s in config.spam_prevention.strategies]
            },
            'timing': {
                'mode': config.timing.mode.value,
                'base_interval_minutes': config.timing.base_interval_minutes,
                'max_interval_minutes': config.timing.max_interval_minutes,
                'min_interval_minutes': config.timing.min_interval_minutes,
                'adaptive_factor': config.timing.adaptive_factor,
                'burst_detection_enabled': config.timing.burst_detection_enabled,
                'user_activity_tracking': config.timing.user_activity_tracking,
                'priority_timing_overrides': config.timing.priority_timing_overrides
            },
            'channel_overrides': config.channel_overrides
        }
    
    def get_channel_config(self, team_id: str, channel_id: str) -> Dict[str, Any]:
        """Get channel-specific configuration overrides."""
        team_config = self.load_team_config(team_id)
        return team_config.channel_overrides.get(channel_id, {})
    
    def apply_channel_overrides(self, base_config: TeamBatchingConfig, channel_id: str) -> TeamBatchingConfig:
        """Apply channel-specific overrides to base configuration."""
        overrides = base_config.channel_overrides.get(channel_id, {})
        if not overrides:
            return base_config
        
        # Create copy of base config
        spam_config = SpamPreventionConfig(**asdict(base_config.spam_prevention))
        timing_config = TimingConfig(**asdict(base_config.timing))
        
        # Apply spam prevention overrides
        spam_overrides = overrides.get('spam_prevention', {})
        for key, value in spam_overrides.items():
            if hasattr(spam_config, key):
                if key == 'strategies':
                    setattr(spam_config, key, [SpamPreventionStrategy(s) for s in value])
                else:
                    setattr(spam_config, key, value)
        
        # Apply timing overrides
        timing_overrides = overrides.get('timing', {})
        for key, value in timing_overrides.items():
            if hasattr(timing_config, key):
                if key == 'mode':
                    setattr(timing_config, key, TimingMode(value))
                else:
                    setattr(timing_config, key, value)
        
        return TeamBatchingConfig(
            team_id=base_config.team_id,
            spam_prevention=spam_config,
            timing=timing_config,
            channel_overrides=base_config.channel_overrides
        )
    
    def validate_config(self, config: TeamBatchingConfig) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Validate spam prevention config
        spam = config.spam_prevention
        if spam.max_messages_per_minute <= 0:
            errors.append("max_messages_per_minute must be positive")
        if spam.max_messages_per_hour <= 0:
            errors.append("max_messages_per_hour must be positive")
        if spam.burst_threshold <= 0:
            errors.append("burst_threshold must be positive")
        if spam.burst_window_seconds <= 0:
            errors.append("burst_window_seconds must be positive")
        if spam.cooldown_after_burst_minutes < 0:
            errors.append("cooldown_after_burst_minutes must be non-negative")
        if not (0 <= spam.quiet_hours_start <= 23):
            errors.append("quiet_hours_start must be between 0 and 23")
        if not (0 <= spam.quiet_hours_end <= 23):
            errors.append("quiet_hours_end must be between 0 and 23")
        
        # Validate timing config
        timing = config.timing
        if timing.base_interval_minutes <= 0:
            errors.append("base_interval_minutes must be positive")
        if timing.max_interval_minutes <= 0:
            errors.append("max_interval_minutes must be positive")
        if timing.min_interval_minutes < 0:
            errors.append("min_interval_minutes must be non-negative")
        if timing.min_interval_minutes >= timing.max_interval_minutes:
            errors.append("min_interval_minutes must be less than max_interval_minutes")
        if timing.adaptive_factor <= 0:
            errors.append("adaptive_factor must be positive")
        
        return errors
    
    def get_all_team_configs(self) -> Dict[str, TeamBatchingConfig]:
        """Get all loaded team configurations."""
        return self._team_configs.copy()
    
    def reload_config(self, team_id: str) -> TeamBatchingConfig:
        """Reload configuration for a team from file."""
        if team_id in self._team_configs:
            del self._team_configs[team_id]
        return self.load_team_config(team_id)


# Global config manager instance
default_batching_config_manager = BatchingConfigManager()