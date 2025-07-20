"""
Core interface functions for the Reflective Pause library.

Provides the main API that both browser extension and Discord bot use.
"""

import logging
import time
from typing import Optional
from enum import Enum

from .toxicity.engine import ToxicityEngine
from .toxicity.onnx_engine import ONNXEngine
from .prompts.generator import generate_prompt as _generate_prompt, PromptData
from .logging.decision_logger import log_decision as _log_decision, DecisionType
from .cache.toxicity_cache import get_global_cache
from .metrics.collector import get_global_collector
from .config.manager import get_global_config

logger = logging.getLogger(__name__)

# Global toxicity engine instance
_toxicity_engine: Optional[ToxicityEngine] = None


def check(text: str, threshold: Optional[float] = None, always_prompt: Optional[bool] = None) -> bool:
    """
    Check if text exceeds toxicity threshold or user has always-prompt setting.
    
    Args:
        text: Text to analyze for toxicity
        threshold: Toxicity threshold (0.0-1.0). If None, uses config default.
        always_prompt: If True, always return True regardless of toxicity. If None, uses config default.
        
    Returns:
        True if text exceeds threshold or always_prompt is enabled
        
    Raises:
        ValueError: If text is empty or threshold is invalid
        RuntimeError: If toxicity engine fails to initialize
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")
    
    # Load configuration
    config = get_global_config()
    
    # Use config defaults if not specified
    if threshold is None:
        threshold = config.toxicity.default_threshold
    if always_prompt is None:
        always_prompt = config.toxicity.always_prompt
    
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Threshold must be between 0.0 and 1.0")
    
    if always_prompt:
        logger.info("Always-prompt setting enabled, returning True")
        return True
    
    try:
        start_time = time.perf_counter()
        
        global _toxicity_engine
        if _toxicity_engine is None:
            _toxicity_engine = ONNXEngine()
        
        # Check cache first
        cache = get_global_cache()
        cached_score = cache.get(text, _toxicity_engine.engine_type)
        
        was_cached = cached_score is not None
        
        if cached_score is not None:
            toxicity_score = cached_score
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(f"Toxicity check (cached): score={toxicity_score:.3f}, threshold={threshold}, duration={duration_ms:.1f}ms")
        else:
            toxicity_score = _toxicity_engine.analyze(text)
            # Cache the result
            cache.put(text, _toxicity_engine.engine_type, toxicity_score)
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(f"Toxicity check (analyzed): score={toxicity_score:.3f}, threshold={threshold}, duration={duration_ms:.1f}ms")
        
        result = toxicity_score > threshold
        
        # Record metrics
        metrics_collector = get_global_collector()
        metrics_collector.record_toxicity_check(
            text=text,
            result=result,
            score=toxicity_score,
            threshold=threshold,
            engine_type=_toxicity_engine.engine_type,
            duration_ms=duration_ms,
            was_cached=was_cached
        )
        
        # Performance warning based on config
        if config.toxicity.performance_monitoring and duration_ms > config.toxicity.latency_warning_threshold_ms:
            logger.warning(f"Toxicity check exceeded {config.toxicity.latency_warning_threshold_ms}ms latency target: {duration_ms:.1f}ms")
        
        return result
        
    except Exception as e:
        # Record error in metrics
        duration_ms = (time.perf_counter() - start_time) * 1000
        metrics_collector = get_global_collector()
        
        engine_type = _toxicity_engine.engine_type if _toxicity_engine else "unknown"
        
        metrics_collector.record_toxicity_check(
            text=text,
            result=False,
            score=0.0,
            threshold=threshold,
            engine_type=engine_type,
            duration_ms=duration_ms,
            was_cached=False,
            error=e
        )
        
        logger.error(f"Toxicity check failed: {e}")
        raise RuntimeError(f"Failed to analyze text: {e}")


def generate_prompt(locale: str = "en") -> PromptData:
    """
    Generate a localized CBT prompt with question rotation.
    
    Args:
        locale: Language locale (e.g., 'en', 'vi')
        
    Returns:
        PromptData object with localized prompt strings
        
    Raises:
        ValueError: If locale is not supported
        RuntimeError: If prompt generation fails
    """
    try:
        return _generate_prompt(locale)
    except Exception as e:
        logger.error(f"Prompt generation failed for locale '{locale}': {e}")
        raise RuntimeError(f"Failed to generate prompt: {e}")


def log_decision(decision: DecisionType) -> None:
    """
    Log anonymized decision data for analytics.
    
    Args:
        decision: The user's decision (enum value)
        
    Raises:
        ValueError: If decision is invalid
        RuntimeError: If logging fails
    """
    try:
        _log_decision(decision)
    except Exception as e:
        logger.error(f"Decision logging failed: {e}")
        raise RuntimeError(f"Failed to log decision: {e}")


# Configure logging
def _configure_logging() -> None:
    """Configure logging for the library."""
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)


_configure_logging()