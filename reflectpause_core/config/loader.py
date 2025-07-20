"""
Configuration loading utilities.
"""

import json
import os
from typing import Dict, Any, Optional
from .manager import ConfigManager, ToxicityConfig, CacheConfig, MetricsConfig, EngineConfig


def load_config(config_file: str) -> ConfigManager:
    """
    Load configuration from file.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        ConfigManager instance with loaded configuration
    """
    return ConfigManager(config_file)


def save_config(config_manager: ConfigManager, config_file: str) -> None:
    """
    Save configuration to file.
    
    Args:
        config_manager: ConfigManager instance to save
        config_file: Path to save configuration file
    """
    config_manager.save_config(config_file)


def get_default_config() -> Dict[str, Any]:
    """
    Get default configuration as dictionary.
    
    Returns:
        Dictionary with default configuration values
    """
    return {
        'toxicity': {
            'default_threshold': 0.7,
            'default_engine': 'onnx',
            'always_prompt': False,
            'max_text_length': 10000,
            'engine_fallback_enabled': True,
            'performance_monitoring': True,
            'latency_warning_threshold_ms': 50
        },
        'cache': {
            'enabled': True,
            'max_size': 1000,
            'ttl_seconds': 3600,
            'cleanup_interval_seconds': 300
        },
        'metrics': {
            'enabled': True,
            'max_samples': 10000,
            'export_format': 'dict',
            'storage_file': None,
            'accuracy_tracking': True
        },
        'engines': {
            'onnx_model_path': None,
            'perspective_api_key': None,
            'perspective_api_timeout': 5,
            'heuristic_enabled': True
        }
    }


def create_sample_config(output_file: str) -> None:
    """
    Create a sample configuration file with defaults and comments.
    
    Args:
        output_file: Path to create sample configuration file
    """
    config = get_default_config()
    
    # Add comments/documentation
    documented_config = {
        "_comments": {
            "toxicity": "Configuration for toxicity detection behavior",
            "cache": "Configuration for result caching",
            "metrics": "Configuration for metrics collection",
            "engines": "Configuration for toxicity detection engines"
        },
        **config
    }
    
    with open(output_file, 'w') as f:
        json.dump(documented_config, f, indent=2)


def validate_config_file(config_file: str) -> tuple[bool, list[str]]:
    """
    Validate a configuration file.
    
    Args:
        config_file: Path to configuration file to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    try:
        if not os.path.exists(config_file):
            return False, [f"Configuration file does not exist: {config_file}"]
        
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # Create temporary config manager to validate
        temp_config = ConfigManager()
        
        # Try to load the configuration
        if 'toxicity' in config_data:
            temp_config._update_dataclass(temp_config.toxicity, config_data['toxicity'])
        
        if 'cache' in config_data:
            temp_config._update_dataclass(temp_config.cache, config_data['cache'])
        
        if 'metrics' in config_data:
            temp_config._update_dataclass(temp_config.metrics, config_data['metrics'])
        
        if 'engines' in config_data:
            temp_config._update_dataclass(temp_config.engines, config_data['engines'])
        
        # Validate the configuration
        errors = temp_config.validate_config()
        
        return len(errors) == 0, errors
        
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON in configuration file: {e}"]
    except Exception as e:
        return False, [f"Error validating configuration file: {e}"]


def merge_configs(base_config: Dict[str, Any], 
                  override_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two configuration dictionaries.
    
    Args:
        base_config: Base configuration dictionary
        override_config: Configuration overrides
        
    Returns:
        Merged configuration dictionary
    """
    merged = base_config.copy()
    
    for section, values in override_config.items():
        if section in merged and isinstance(merged[section], dict) and isinstance(values, dict):
            merged[section].update(values)
        else:
            merged[section] = values
    
    return merged


def get_config_from_env() -> Dict[str, Any]:
    """
    Extract configuration from environment variables.
    
    Returns:
        Configuration dictionary from environment variables
    """
    config = {
        'toxicity': {},
        'cache': {},
        'metrics': {},
        'engines': {}
    }
    
    env_mappings = {
        'REFLECTPAUSE_THRESHOLD': ('toxicity', 'default_threshold', float),
        'REFLECTPAUSE_ENGINE': ('toxicity', 'default_engine', str),
        'REFLECTPAUSE_ALWAYS_PROMPT': ('toxicity', 'always_prompt', lambda x: x.lower() == 'true'),
        'REFLECTPAUSE_MAX_TEXT_LENGTH': ('toxicity', 'max_text_length', int),
        'REFLECTPAUSE_CACHE_SIZE': ('cache', 'max_size', int),
        'REFLECTPAUSE_CACHE_TTL': ('cache', 'ttl_seconds', int),
        'REFLECTPAUSE_CACHE_ENABLED': ('cache', 'enabled', lambda x: x.lower() == 'true'),
        'REFLECTPAUSE_METRICS_ENABLED': ('metrics', 'enabled', lambda x: x.lower() == 'true'),
        'REFLECTPAUSE_METRICS_SAMPLES': ('metrics', 'max_samples', int),
        'REFLECTPAUSE_ONNX_MODEL_PATH': ('engines', 'onnx_model_path', str),
        'REFLECTPAUSE_API_KEY': ('engines', 'perspective_api_key', str),
        'REFLECTPAUSE_API_TIMEOUT': ('engines', 'perspective_api_timeout', int),
    }
    
    for env_var, (section, field, converter) in env_mappings.items():
        value = os.getenv(env_var)
        if value is not None:
            try:
                config[section][field] = converter(value)
            except Exception:
                # Ignore invalid environment values
                pass
    
    # Remove empty sections
    return {k: v for k, v in config.items() if v}


def create_config_from_template(template_name: str, output_file: str) -> None:
    """
    Create configuration file from a predefined template.
    
    Args:
        template_name: Name of the template ('default', 'high_performance', 'secure')
        output_file: Path to create configuration file
    """
    templates = {
        'default': get_default_config(),
        
        'high_performance': {
            **get_default_config(),
            'toxicity': {
                **get_default_config()['toxicity'],
                'default_threshold': 0.8,  # Higher threshold for fewer false positives
                'latency_warning_threshold_ms': 25  # Stricter performance requirement
            },
            'cache': {
                **get_default_config()['cache'],
                'max_size': 5000,  # Larger cache
                'ttl_seconds': 7200,  # Longer TTL
            },
            'metrics': {
                **get_default_config()['metrics'],
                'max_samples': 50000,  # More samples for better analysis
            }
        },
        
        'secure': {
            **get_default_config(),
            'toxicity': {
                **get_default_config()['toxicity'],
                'default_threshold': 0.5,  # Lower threshold for more sensitivity
                'default_engine': 'onnx',  # Prefer on-device processing
            },
            'cache': {
                **get_default_config()['cache'],
                'ttl_seconds': 1800,  # Shorter TTL for fresher results
            },
            'metrics': {
                **get_default_config()['metrics'],
                'accuracy_tracking': True,  # Enhanced accuracy tracking
            },
            'engines': {
                **get_default_config()['engines'],
                'perspective_api_key': None,  # Disable cloud API
                'heuristic_enabled': True,
            }
        }
    }
    
    if template_name not in templates:
        raise ValueError(f"Unknown template: {template_name}. Available: {list(templates.keys())}")
    
    config = templates[template_name]
    
    with open(output_file, 'w') as f:
        json.dump(config, f, indent=2)