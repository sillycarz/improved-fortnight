"""
Configuration management for toxicity detection settings.
"""

import os
import json
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToxicityConfig:
    """Configuration for toxicity detection."""
    default_threshold: float = 0.7
    default_engine: str = "onnx"
    always_prompt: bool = False
    max_text_length: int = 10000
    engine_fallback_enabled: bool = True
    performance_monitoring: bool = True
    latency_warning_threshold_ms: int = 50


@dataclass
class CacheConfig:
    """Configuration for caching."""
    enabled: bool = True
    max_size: int = 1000
    ttl_seconds: int = 3600
    cleanup_interval_seconds: int = 300


@dataclass
class MetricsConfig:
    """Configuration for metrics collection."""
    enabled: bool = True
    max_samples: int = 10000
    export_format: str = "dict"
    storage_file: Optional[str] = None
    accuracy_tracking: bool = True


@dataclass
class EngineConfig:
    """Configuration for specific engines."""
    onnx_model_path: Optional[str] = None
    perspective_api_key: Optional[str] = None
    perspective_api_timeout: int = 5
    heuristic_enabled: bool = True


class ConfigManager:
    """
    Thread-safe configuration manager for the Reflective Pause library.
    
    Manages configuration loading, validation, and runtime updates.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file. If None, uses default locations.
        """
        self.config_file = config_file or self._get_default_config_path()
        self._lock = threading.RLock()
        
        # Configuration sections
        self.toxicity = ToxicityConfig()
        self.cache = CacheConfig()
        self.metrics = MetricsConfig()
        self.engines = EngineConfig()
        
        # Configuration overrides from environment
        self._env_overrides: Dict[str, Any] = {}
        
        # Load configuration
        self.load_config()
        self._apply_env_overrides()
    
    def load_config(self, config_file: Optional[str] = None) -> None:
        """
        Load configuration from file.
        
        Args:
            config_file: Path to configuration file. If None, uses instance default.
        """
        file_path = config_file or self.config_file
        
        with self._lock:
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        config_data = json.load(f)
                    
                    # Update configuration sections
                    if 'toxicity' in config_data:
                        self._update_dataclass(self.toxicity, config_data['toxicity'])
                    
                    if 'cache' in config_data:
                        self._update_dataclass(self.cache, config_data['cache'])
                    
                    if 'metrics' in config_data:
                        self._update_dataclass(self.metrics, config_data['metrics'])
                    
                    if 'engines' in config_data:
                        self._update_dataclass(self.engines, config_data['engines'])
                    
                    logger.info(f"Loaded configuration from {file_path}")
                else:
                    logger.info(f"No configuration file found at {file_path}, using defaults")
                    
            except Exception as e:
                logger.error(f"Failed to load configuration from {file_path}: {e}")
                logger.info("Using default configuration")
    
    def save_config(self, config_file: Optional[str] = None) -> None:
        """
        Save current configuration to file.
        
        Args:
            config_file: Path to save configuration. If None, uses instance default.
        """
        file_path = config_file or self.config_file
        
        with self._lock:
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                config_data = {
                    'toxicity': asdict(self.toxicity),
                    'cache': asdict(self.cache),
                    'metrics': asdict(self.metrics),
                    'engines': asdict(self.engines)
                }
                
                with open(file_path, 'w') as f:
                    json.dump(config_data, f, indent=2)
                
                logger.info(f"Saved configuration to {file_path}")
                
            except Exception as e:
                logger.error(f"Failed to save configuration to {file_path}: {e}")
    
    def update_config(self, section: str, updates: Dict[str, Any]) -> None:
        """
        Update configuration section with new values.
        
        Args:
            section: Configuration section ('toxicity', 'cache', 'metrics', 'engines')
            updates: Dictionary of field names and new values
            
        Raises:
            ValueError: If section is invalid or updates contain invalid fields
        """
        with self._lock:
            if section == 'toxicity':
                target = self.toxicity
            elif section == 'cache':
                target = self.cache
            elif section == 'metrics':
                target = self.metrics
            elif section == 'engines':
                target = self.engines
            else:
                raise ValueError(f"Invalid configuration section: {section}")
            
            # Validate updates
            valid_fields = set(asdict(target).keys())
            invalid_fields = set(updates.keys()) - valid_fields
            if invalid_fields:
                raise ValueError(f"Invalid fields for {section}: {invalid_fields}")
            
            # Apply updates
            for field, value in updates.items():
                if hasattr(target, field):
                    # Validate type if possible
                    current_value = getattr(target, field)
                    if current_value is not None and not isinstance(value, type(current_value)):
                        try:
                            # Try to convert to correct type
                            value = type(current_value)(value)
                        except (ValueError, TypeError):
                            raise ValueError(f"Invalid type for {section}.{field}: "
                                           f"expected {type(current_value)}, got {type(value)}")
                    
                    setattr(target, field, value)
                    logger.debug(f"Updated {section}.{field} = {value}")
    
    def get_config_dict(self) -> Dict[str, Any]:
        """
        Get complete configuration as dictionary.
        
        Returns:
            Dictionary with all configuration sections
        """
        with self._lock:
            return {
                'toxicity': asdict(self.toxicity),
                'cache': asdict(self.cache),
                'metrics': asdict(self.metrics),
                'engines': asdict(self.engines)
            }
    
    def reset_to_defaults(self) -> None:
        """Reset all configuration to default values."""
        with self._lock:
            self.toxicity = ToxicityConfig()
            self.cache = CacheConfig()
            self.metrics = MetricsConfig()
            self.engines = EngineConfig()
            
            logger.info("Reset configuration to defaults")
    
    def validate_config(self) -> List[str]:
        """
        Validate current configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        with self._lock:
            # Validate toxicity config
            if not 0.0 <= self.toxicity.default_threshold <= 1.0:
                errors.append("toxicity.default_threshold must be between 0.0 and 1.0")
            
            if self.toxicity.max_text_length <= 0:
                errors.append("toxicity.max_text_length must be positive")
            
            if self.toxicity.latency_warning_threshold_ms <= 0:
                errors.append("toxicity.latency_warning_threshold_ms must be positive")
            
            # Validate cache config
            if self.cache.max_size <= 0:
                errors.append("cache.max_size must be positive")
            
            if self.cache.ttl_seconds <= 0:
                errors.append("cache.ttl_seconds must be positive")
            
            if self.cache.cleanup_interval_seconds <= 0:
                errors.append("cache.cleanup_interval_seconds must be positive")
            
            # Validate metrics config
            if self.metrics.max_samples <= 0:
                errors.append("metrics.max_samples must be positive")
            
            if self.metrics.export_format not in ['dict', 'prometheus']:
                errors.append("metrics.export_format must be 'dict' or 'prometheus'")
            
            # Validate engine config
            if (self.engines.onnx_model_path and 
                not os.path.exists(self.engines.onnx_model_path)):
                errors.append(f"engines.onnx_model_path does not exist: {self.engines.onnx_model_path}")
            
            if self.engines.perspective_api_timeout <= 0:
                errors.append("engines.perspective_api_timeout must be positive")
        
        return errors
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        # Try common configuration locations
        config_locations = [
            os.path.join(os.getcwd(), 'reflectpause_config.json'),
            os.path.join(os.path.expanduser('~'), '.reflectpause', 'config.json'),
            os.path.join('/etc', 'reflectpause', 'config.json')
        ]
        
        # Use first existing file, or default to first location for creation
        for location in config_locations:
            if os.path.exists(location):
                return location
        
        return config_locations[0]
    
    def _update_dataclass(self, target: object, updates: Dict[str, Any]) -> None:
        """Update dataclass fields from dictionary."""
        for field, value in updates.items():
            if hasattr(target, field):
                setattr(target, field, value)
    
    def _apply_env_overrides(self) -> None:
        """Apply configuration overrides from environment variables."""
        env_mappings = {
            'REFLECTPAUSE_THRESHOLD': ('toxicity', 'default_threshold', float),
            'REFLECTPAUSE_ENGINE': ('toxicity', 'default_engine', str),
            'REFLECTPAUSE_ALWAYS_PROMPT': ('toxicity', 'always_prompt', lambda x: x.lower() == 'true'),
            'REFLECTPAUSE_CACHE_SIZE': ('cache', 'max_size', int),
            'REFLECTPAUSE_CACHE_TTL': ('cache', 'ttl_seconds', int),
            'REFLECTPAUSE_CACHE_ENABLED': ('cache', 'enabled', lambda x: x.lower() == 'true'),
            'REFLECTPAUSE_METRICS_ENABLED': ('metrics', 'enabled', lambda x: x.lower() == 'true'),
            'REFLECTPAUSE_ONNX_MODEL_PATH': ('engines', 'onnx_model_path', str),
            'REFLECTPAUSE_API_KEY': ('engines', 'perspective_api_key', str),
        }
        
        for env_var, (section, field, converter) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    converted_value = converter(value)
                    self.update_config(section, {field: converted_value})
                    logger.info(f"Applied environment override: {env_var} -> {section}.{field}")
                except Exception as e:
                    logger.warning(f"Failed to apply environment override {env_var}: {e}")


# Global configuration manager instance
_global_config: Optional[ConfigManager] = None


def get_global_config(config_file: Optional[str] = None) -> ConfigManager:
    """
    Get or create global configuration manager instance.
    
    Args:
        config_file: Configuration file path (only used on first call)
        
    Returns:
        Global ConfigManager instance
    """
    global _global_config
    if _global_config is None:
        _global_config = ConfigManager(config_file)
    return _global_config


def reload_global_config() -> None:
    """Reload the global configuration from file."""
    global _global_config
    if _global_config is not None:
        _global_config.load_config()