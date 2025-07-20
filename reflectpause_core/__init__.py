"""
Reflective Pause Core Library

A shared Python library providing toxicity checking and prompt generation
for the Reflective Pause Bot system.
"""

from .core import check, generate_prompt, log_decision
from .async_core import (
    check_async, check_batch_async, generate_prompt_async, log_decision_async,
    check_with_prompt_async, complete_workflow_async, AsyncToxicityChecker
)
from .cache.toxicity_cache import get_global_cache, clear_global_cache
from .metrics.collector import get_global_collector, reset_global_metrics
from .metrics.accuracy import get_global_tracker
from .config.manager import get_global_config, reload_global_config
from .prompts.generator import (
    get_available_locales, normalize_locale, detect_language_from_text,
    supports_locale, generate_prompt_auto_detect
)

__version__ = "0.3.0"
__all__ = [
    # Core sync functions
    "check", "generate_prompt", "log_decision",
    
    # Async functions
    "check_async", "check_batch_async", "generate_prompt_async", "log_decision_async",
    "check_with_prompt_async", "complete_workflow_async", "AsyncToxicityChecker",
    
    # Cache management
    "get_global_cache", "clear_global_cache",
    
    # Metrics and monitoring
    "get_global_collector", "reset_global_metrics", "get_global_tracker",
    
    # Configuration
    "get_global_config", "reload_global_config",
    
    # Multilingual support
    "get_available_locales", "normalize_locale", "detect_language_from_text",
    "supports_locale", "generate_prompt_auto_detect"
]