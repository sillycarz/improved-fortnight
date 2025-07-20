"""
Async interface functions for the Reflective Pause library.

Provides async versions of core functions for better performance in async applications.
"""

import asyncio
import logging
import time
from typing import Optional, List, Tuple
from enum import Enum

from .toxicity.engine import ToxicityEngine
from .toxicity.onnx_engine import ONNXEngine
from .prompts.generator import generate_prompt as _generate_prompt, PromptData
from .logging.decision_logger import log_decision as _log_decision, DecisionType
from .cache.toxicity_cache import get_global_cache
from .metrics.collector import get_global_collector
from .config.manager import get_global_config

logger = logging.getLogger(__name__)

# Global async toxicity engine instance
_async_toxicity_engine: Optional[ToxicityEngine] = None
_engine_lock = asyncio.Lock()


async def check_async(text: str, threshold: Optional[float] = None, always_prompt: Optional[bool] = None) -> bool:
    """
    Async version of toxicity check function.
    
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
        
        # Initialize engine if needed (thread-safe)
        global _async_toxicity_engine
        if _async_toxicity_engine is None:
            async with _engine_lock:
                if _async_toxicity_engine is None:
                    _async_toxicity_engine = ONNXEngine()
        
        # Check cache first
        cache = get_global_cache()
        cached_score = cache.get(text, _async_toxicity_engine.engine_type)
        
        was_cached = cached_score is not None
        
        if cached_score is not None:
            toxicity_score = cached_score
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(f"Async toxicity check (cached): score={toxicity_score:.3f}, threshold={threshold}, duration={duration_ms:.1f}ms")
        else:
            # Run analysis in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            toxicity_score = await loop.run_in_executor(None, _async_toxicity_engine.analyze, text)
            
            # Cache the result
            cache.put(text, _async_toxicity_engine.engine_type, toxicity_score)
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(f"Async toxicity check (analyzed): score={toxicity_score:.3f}, threshold={threshold}, duration={duration_ms:.1f}ms")
        
        result = toxicity_score > threshold
        
        # Record metrics
        metrics_collector = get_global_collector()
        metrics_collector.record_toxicity_check(
            text=text,
            result=result,
            score=toxicity_score,
            threshold=threshold,
            engine_type=_async_toxicity_engine.engine_type,
            duration_ms=duration_ms,
            was_cached=was_cached
        )
        
        # Performance warning based on config
        if config.toxicity.performance_monitoring and duration_ms > config.toxicity.latency_warning_threshold_ms:
            logger.warning(f"Async toxicity check exceeded {config.toxicity.latency_warning_threshold_ms}ms latency target: {duration_ms:.1f}ms")
        
        return result
        
    except Exception as e:
        # Record error in metrics
        duration_ms = (time.perf_counter() - start_time) * 1000
        metrics_collector = get_global_collector()
        
        engine_type = _async_toxicity_engine.engine_type if _async_toxicity_engine else "unknown"
        
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
        
        logger.error(f"Async toxicity check failed: {e}")
        raise RuntimeError(f"Failed to analyze text: {e}")


async def check_batch_async(texts: List[str], threshold: Optional[float] = None, always_prompt: Optional[bool] = None) -> List[bool]:
    """
    Async batch toxicity check for multiple texts.
    
    Args:
        texts: List of texts to analyze for toxicity
        threshold: Toxicity threshold (0.0-1.0). If None, uses config default.
        always_prompt: If True, always return True regardless of toxicity. If None, uses config default.
        
    Returns:
        List of boolean results corresponding to input texts
        
    Raises:
        ValueError: If any text is empty or threshold is invalid
        RuntimeError: If toxicity engine fails
    """
    if not texts:
        return []
    
    # Validate all texts first
    for i, text in enumerate(texts):
        if not text or not text.strip():
            raise ValueError(f"Text at index {i} cannot be empty")
    
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
        logger.info("Always-prompt setting enabled, returning True for all texts")
        return [True] * len(texts)
    
    # Process texts concurrently
    tasks = [check_async(text, threshold, False) for text in texts]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle any exceptions
    final_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Failed to analyze text at index {i}: {result}")
            raise RuntimeError(f"Failed to analyze text at index {i}: {result}")
        final_results.append(result)
    
    return final_results


async def generate_prompt_async(locale: str = "en") -> PromptData:
    """
    Async version of prompt generation function.
    
    Args:
        locale: Language locale (e.g., 'en', 'vi')
        
    Returns:
        PromptData object with localized prompt strings
        
    Raises:
        ValueError: If locale is not supported
        RuntimeError: If prompt generation fails
    """
    try:
        # Run in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _generate_prompt, locale)
    except Exception as e:
        logger.error(f"Async prompt generation failed for locale '{locale}': {e}")
        raise RuntimeError(f"Failed to generate prompt: {e}")


async def log_decision_async(decision: DecisionType) -> None:
    """
    Async version of decision logging function.
    
    Args:
        decision: The user's decision (enum value)
        
    Raises:
        ValueError: If decision is invalid
        RuntimeError: If logging fails
    """
    try:
        # Run in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _log_decision, decision)
    except Exception as e:
        logger.error(f"Async decision logging failed: {e}")
        raise RuntimeError(f"Failed to log decision: {e}")


async def check_with_prompt_async(text: str, locale: str = "en", threshold: Optional[float] = None) -> Tuple[bool, Optional[PromptData]]:
    """
    Async combined function to check toxicity and generate prompt if needed.
    
    Args:
        text: Text to analyze for toxicity
        locale: Language locale for prompt generation
        threshold: Toxicity threshold. If None, uses config default.
        
    Returns:
        Tuple of (needs_prompt, prompt_data)
        
    Raises:
        ValueError: If text is empty or parameters are invalid
        RuntimeError: If analysis or prompt generation fails
    """
    # Check toxicity first
    needs_prompt = await check_async(text, threshold)
    
    if needs_prompt:
        # Generate prompt
        prompt = await generate_prompt_async(locale)
        return True, prompt
    else:
        return False, None


async def complete_workflow_async(text: str, 
                                locale: str = "en", 
                                threshold: Optional[float] = None,
                                decision: Optional[DecisionType] = None) -> dict:
    """
    Complete async workflow: check -> prompt -> log decision.
    
    Args:
        text: Text to analyze for toxicity
        locale: Language locale for prompt generation
        threshold: Toxicity threshold. If None, uses config default.
        decision: User decision to log. If None, no logging is performed.
        
    Returns:
        Dictionary with workflow results
    """
    start_time = time.perf_counter()
    
    # Step 1: Check toxicity and generate prompt if needed
    needs_prompt, prompt = await check_with_prompt_async(text, locale, threshold)
    
    # Step 2: Log decision if provided
    if decision is not None:
        await log_decision_async(decision)
    
    duration_ms = (time.perf_counter() - start_time) * 1000
    
    return {
        'needs_prompt': needs_prompt,
        'prompt': prompt,
        'decision_logged': decision is not None,
        'total_duration_ms': duration_ms
    }


class AsyncToxicityChecker:
    """
    Async context manager for toxicity checking with resource management.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize async toxicity checker.
        
        Args:
            config_file: Optional configuration file path
        """
        self.config_file = config_file
        self.engine: Optional[ToxicityEngine] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        # Initialize configuration if specified
        if self.config_file:
            config = get_global_config(self.config_file)
        
        # Initialize engine
        self.engine = ONNXEngine()
        
        # Pre-warm cache and engine if needed
        await self._warmup()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.engine:
            # Clean up engine resources in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.engine.cleanup)
    
    async def check(self, text: str, threshold: Optional[float] = None) -> bool:
        """Check toxicity using this instance's engine."""
        if not self.engine:
            raise RuntimeError("Engine not initialized. Use async context manager.")
        
        return await check_async(text, threshold)
    
    async def check_batch(self, texts: List[str], threshold: Optional[float] = None) -> List[bool]:
        """Check multiple texts for toxicity."""
        if not self.engine:
            raise RuntimeError("Engine not initialized. Use async context manager.")
        
        return await check_batch_async(texts, threshold)
    
    async def _warmup(self) -> None:
        """Warm up engine and cache with test content."""
        try:
            # Run a small test to ensure engine is ready
            await check_async("test warmup message", threshold=0.5)
            logger.debug("Async toxicity checker warmed up successfully")
        except Exception as e:
            logger.warning(f"Warmup failed: {e}")


# Utility functions for async integration

async def get_cache_stats_async() -> dict:
    """Get cache statistics asynchronously."""
    loop = asyncio.get_event_loop()
    cache = get_global_cache()
    return await loop.run_in_executor(None, cache.get_stats)


async def get_metrics_summary_async() -> dict:
    """Get metrics summary asynchronously."""
    loop = asyncio.get_event_loop()
    collector = get_global_collector()
    return await loop.run_in_executor(None, collector.get_summary)


async def cleanup_cache_async() -> int:
    """Clean up expired cache entries asynchronously."""
    loop = asyncio.get_event_loop()
    cache = get_global_cache()
    return await loop.run_in_executor(None, cache.cleanup_expired)