"""
Caching layer for toxicity detection results.
"""

import hashlib
import time
import threading
from typing import Dict, Optional, NamedTuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheResult:
    """Container for cached toxicity analysis results."""
    text_hash: str
    toxicity_score: float
    timestamp: float
    engine_type: str
    hit_count: int = 0


class ToxicityCache:
    """
    Thread-safe LRU cache for toxicity detection results.
    
    Provides caching with TTL (time-to-live) and size limits to improve
    performance for repeated toxicity checks.
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Initialize the toxicity cache.
        
        Args:
            max_size: Maximum number of cached results
            ttl_seconds: Time-to-live for cached results in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, CacheResult] = {}
        self._access_times: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired': 0
        }
    
    def get(self, text: str, engine_type: str) -> Optional[float]:
        """
        Get cached toxicity score for text.
        
        Args:
            text: Text to look up
            engine_type: Engine that would analyze the text
            
        Returns:
            Cached toxicity score if available and valid, None otherwise
        """
        cache_key = self._generate_key(text, engine_type)
        
        with self._lock:
            if cache_key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            result = self._cache[cache_key]
            
            # Check if result has expired
            if self._is_expired(result):
                del self._cache[cache_key]
                del self._access_times[cache_key]
                self._stats['expired'] += 1
                self._stats['misses'] += 1
                return None
            
            # Update access time and hit count
            self._access_times[cache_key] = time.time()
            result.hit_count += 1
            self._stats['hits'] += 1
            
            logger.debug(f"Cache hit for text hash {cache_key[:8]}... (score: {result.toxicity_score:.3f})")
            return result.toxicity_score
    
    def put(self, text: str, engine_type: str, toxicity_score: float) -> None:
        """
        Cache toxicity score for text.
        
        Args:
            text: Text that was analyzed
            engine_type: Engine that analyzed the text
            toxicity_score: Toxicity score to cache
        """
        cache_key = self._generate_key(text, engine_type)
        current_time = time.time()
        
        with self._lock:
            # Check if we need to evict entries
            if len(self._cache) >= self.max_size and cache_key not in self._cache:
                self._evict_lru()
            
            # Store the result
            self._cache[cache_key] = CacheResult(
                text_hash=cache_key,
                toxicity_score=toxicity_score,
                timestamp=current_time,
                engine_type=engine_type
            )
            self._access_times[cache_key] = current_time
            
            logger.debug(f"Cached result for text hash {cache_key[:8]}... (score: {toxicity_score:.3f})")
    
    def invalidate(self, text: str = None, engine_type: str = None) -> int:
        """
        Invalidate cached entries.
        
        Args:
            text: Specific text to invalidate. If None, invalidates by engine_type.
            engine_type: Engine type to invalidate. If None with text, invalidates specific text.
            
        Returns:
            Number of entries invalidated
        """
        with self._lock:
            if text is not None:
                cache_key = self._generate_key(text, engine_type or '')
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    del self._access_times[cache_key]
                    return 1
                return 0
            
            if engine_type is not None:
                keys_to_remove = [
                    key for key, result in self._cache.items()
                    if result.engine_type == engine_type
                ]
                for key in keys_to_remove:
                    del self._cache[key]
                    del self._access_times[key]
                return len(keys_to_remove)
            
            # Clear all
            count = len(self._cache)
            self._cache.clear()
            self._access_times.clear()
            return count
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            Number of expired entries removed
        """
        with self._lock:
            expired_keys = [
                key for key, result in self._cache.items()
                if self._is_expired(result)
            ]
            
            for key in expired_keys:
                del self._cache[key]
                del self._access_times[key]
            
            if expired_keys:
                self._stats['expired'] += len(expired_keys)
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache performance statistics
        """
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests) if total_requests > 0 else 0.0
            
            return {
                **self._stats.copy(),
                'size': len(self._cache),
                'hit_rate': hit_rate,
                'total_requests': total_requests
            }
    
    def reset_stats(self) -> None:
        """Reset cache statistics."""
        with self._lock:
            self._stats = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'expired': 0
            }
    
    def _generate_key(self, text: str, engine_type: str) -> str:
        """Generate cache key for text and engine type."""
        # Include engine type in hash to handle different engines differently
        combined = f"{engine_type}:{text}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    def _is_expired(self, result: CacheResult) -> bool:
        """Check if cache result has expired."""
        return time.time() - result.timestamp > self.ttl_seconds
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._access_times:
            return
        
        # Find least recently used entry
        lru_key = min(self._access_times, key=self._access_times.get)
        
        # Remove from cache
        del self._cache[lru_key]
        del self._access_times[lru_key]
        self._stats['evictions'] += 1
        
        logger.debug(f"Evicted LRU cache entry: {lru_key[:8]}...")


# Global cache instance
_global_cache: Optional[ToxicityCache] = None


def get_global_cache(max_size: int = 1000, ttl_seconds: int = 3600) -> ToxicityCache:
    """
    Get or create global toxicity cache instance.
    
    Args:
        max_size: Maximum cache size (only used on first call)
        ttl_seconds: TTL in seconds (only used on first call)
        
    Returns:
        Global ToxicityCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = ToxicityCache(max_size, ttl_seconds)
    return _global_cache


def clear_global_cache() -> None:
    """Clear the global cache instance."""
    global _global_cache
    if _global_cache is not None:
        _global_cache.invalidate()