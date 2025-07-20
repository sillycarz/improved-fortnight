"""
Metrics collection for toxicity detection performance and accuracy.
"""

import time
import threading
from typing import Dict, List, Optional, NamedTuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import statistics
import logging

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics collected."""
    TOXICITY_CHECK = "toxicity_check"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    ENGINE_ERROR = "engine_error"
    PERFORMANCE = "performance"


@dataclass
class ToxicityMetrics:
    """Metrics for toxicity detection results."""
    total_checks: int = 0
    toxic_detected: int = 0
    non_toxic_detected: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    engine_errors: int = 0
    
    @property
    def toxicity_rate(self) -> float:
        """Calculate percentage of content detected as toxic."""
        if self.total_checks == 0:
            return 0.0
        return (self.toxic_detected / self.total_checks) * 100
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total_cache_attempts = self.cache_hits + self.cache_misses
        if total_cache_attempts == 0:
            return 0.0
        return (self.cache_hits / total_cache_attempts) * 100
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage."""
        if self.total_checks == 0:
            return 0.0
        return (self.engine_errors / self.total_checks) * 100


@dataclass
class PerformanceMetrics:
    """Performance metrics for toxicity detection."""
    response_times: List[float] = field(default_factory=list)
    cached_response_times: List[float] = field(default_factory=list)
    analyzed_response_times: List[float] = field(default_factory=list)
    
    @property
    def avg_response_time(self) -> float:
        """Average response time in milliseconds."""
        if not self.response_times:
            return 0.0
        return statistics.mean(self.response_times)
    
    @property
    def p95_response_time(self) -> float:
        """95th percentile response time in milliseconds."""
        if not self.response_times:
            return 0.0
        if len(self.response_times) == 1:
            return self.response_times[0]
        
        sorted_times = sorted(self.response_times)
        index = int(0.95 * len(sorted_times))
        return sorted_times[min(index, len(sorted_times) - 1)]
    
    @property
    def avg_cached_time(self) -> float:
        """Average cached response time in milliseconds."""
        if not self.cached_response_times:
            return 0.0
        return statistics.mean(self.cached_response_times)
    
    @property
    def avg_analyzed_time(self) -> float:
        """Average analysis response time in milliseconds."""
        if not self.analyzed_response_times:
            return 0.0
        return statistics.mean(self.analyzed_response_times)
    
    @property
    def cache_speedup(self) -> float:
        """Calculate speedup factor from caching."""
        if not self.cached_response_times or not self.analyzed_response_times:
            return 1.0
        return self.avg_analyzed_time / self.avg_cached_time


class MetricsCollector:
    """
    Thread-safe collector for toxicity detection metrics.
    
    Collects performance data, accuracy metrics, and usage statistics
    for analysis and monitoring.
    """
    
    def __init__(self, max_samples: int = 10000):
        """
        Initialize metrics collector.
        
        Args:
            max_samples: Maximum number of performance samples to keep
        """
        self.max_samples = max_samples
        self._lock = threading.RLock()
        
        # Metrics storage
        self.toxicity_metrics = ToxicityMetrics()
        self.performance_metrics = PerformanceMetrics()
        
        # Detailed tracking
        self._hourly_stats: Dict[str, Dict] = {}  # hour -> stats
        self._engine_stats: Dict[str, ToxicityMetrics] = {}  # engine -> metrics
        
        # Session tracking
        self.session_start = datetime.now(timezone.utc)
        self.last_reset = datetime.now(timezone.utc)
    
    def record_toxicity_check(self, 
                             text: str,
                             result: bool, 
                             score: float,
                             threshold: float,
                             engine_type: str,
                             duration_ms: float,
                             was_cached: bool,
                             error: Optional[Exception] = None) -> None:
        """
        Record a toxicity check event.
        
        Args:
            text: Text that was analyzed
            result: Whether text was classified as toxic
            score: Toxicity score from engine
            threshold: Threshold used for classification
            engine_type: Type of engine used
            duration_ms: Time taken for check in milliseconds
            was_cached: Whether result came from cache
            error: Any error that occurred during check
        """
        with self._lock:
            # Update toxicity metrics
            self.toxicity_metrics.total_checks += 1
            
            if error:
                self.toxicity_metrics.engine_errors += 1
                logger.warning(f"Engine error recorded: {error}")
                return
            
            if result:
                self.toxicity_metrics.toxic_detected += 1
            else:
                self.toxicity_metrics.non_toxic_detected += 1
            
            if was_cached:
                self.toxicity_metrics.cache_hits += 1
            else:
                self.toxicity_metrics.cache_misses += 1
            
            # Update performance metrics
            self.performance_metrics.response_times.append(duration_ms)
            
            if was_cached:
                self.performance_metrics.cached_response_times.append(duration_ms)
            else:
                self.performance_metrics.analyzed_response_times.append(duration_ms)
            
            # Limit sample size
            self._trim_samples()
            
            # Update engine-specific stats
            if engine_type not in self._engine_stats:
                self._engine_stats[engine_type] = ToxicityMetrics()
            
            engine_metrics = self._engine_stats[engine_type]
            engine_metrics.total_checks += 1
            if result:
                engine_metrics.toxic_detected += 1
            else:
                engine_metrics.non_toxic_detected += 1
            
            # Update hourly stats
            self._update_hourly_stats(result, score, threshold, engine_type, duration_ms)
            
            logger.debug(f"Recorded toxicity check: result={result}, score={score:.3f}, "
                        f"engine={engine_type}, duration={duration_ms:.1f}ms, cached={was_cached}")
    
    def get_summary(self) -> Dict:
        """
        Get comprehensive metrics summary.
        
        Returns:
            Dictionary with all collected metrics
        """
        with self._lock:
            uptime_seconds = (datetime.now(timezone.utc) - self.session_start).total_seconds()
            
            return {
                'session': {
                    'uptime_seconds': uptime_seconds,
                    'start_time': self.session_start.isoformat(),
                    'last_reset': self.last_reset.isoformat()
                },
                'toxicity': {
                    'total_checks': self.toxicity_metrics.total_checks,
                    'toxic_detected': self.toxicity_metrics.toxic_detected,
                    'non_toxic_detected': self.toxicity_metrics.non_toxic_detected,
                    'toxicity_rate': self.toxicity_metrics.toxicity_rate,
                    'cache_hits': self.toxicity_metrics.cache_hits,
                    'cache_misses': self.toxicity_metrics.cache_misses,
                    'cache_hit_rate': self.toxicity_metrics.cache_hit_rate,
                    'engine_errors': self.toxicity_metrics.engine_errors,
                    'error_rate': self.toxicity_metrics.error_rate
                },
                'performance': {
                    'avg_response_time_ms': self.performance_metrics.avg_response_time,
                    'p95_response_time_ms': self.performance_metrics.p95_response_time,
                    'avg_cached_time_ms': self.performance_metrics.avg_cached_time,
                    'avg_analyzed_time_ms': self.performance_metrics.avg_analyzed_time,
                    'cache_speedup_factor': self.performance_metrics.cache_speedup,
                    'total_samples': len(self.performance_metrics.response_times)
                },
                'engines': {
                    engine: {
                        'total_checks': metrics.total_checks,
                        'toxic_detected': metrics.toxic_detected,
                        'toxicity_rate': metrics.toxicity_rate,
                        'error_rate': metrics.error_rate
                    }
                    for engine, metrics in self._engine_stats.items()
                }
            }
    
    def get_hourly_breakdown(self) -> Dict[str, Dict]:
        """Get hourly statistics breakdown."""
        with self._lock:
            return self._hourly_stats.copy()
    
    def reset_metrics(self) -> None:
        """Reset all collected metrics."""
        with self._lock:
            self.toxicity_metrics = ToxicityMetrics()
            self.performance_metrics = PerformanceMetrics()
            self._hourly_stats.clear()
            self._engine_stats.clear()
            self.last_reset = datetime.now(timezone.utc)
            
            logger.info("Metrics reset")
    
    def export_metrics(self, format: str = 'dict') -> Dict:
        """
        Export metrics in specified format.
        
        Args:
            format: Export format ('dict', 'prometheus', etc.)
            
        Returns:
            Metrics in requested format
        """
        if format == 'dict':
            return self.get_summary()
        elif format == 'prometheus':
            return self._to_prometheus_format()
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _trim_samples(self) -> None:
        """Trim performance samples to max size."""
        if len(self.performance_metrics.response_times) > self.max_samples:
            # Keep most recent samples
            excess = len(self.performance_metrics.response_times) - self.max_samples
            self.performance_metrics.response_times = \
                self.performance_metrics.response_times[excess:]
            
            if self.performance_metrics.cached_response_times:
                self.performance_metrics.cached_response_times = \
                    self.performance_metrics.cached_response_times[max(0, len(self.performance_metrics.cached_response_times) - self.max_samples//2):]
            
            if self.performance_metrics.analyzed_response_times:
                self.performance_metrics.analyzed_response_times = \
                    self.performance_metrics.analyzed_response_times[max(0, len(self.performance_metrics.analyzed_response_times) - self.max_samples//2):]
    
    def _update_hourly_stats(self, result: bool, score: float, threshold: float, 
                           engine_type: str, duration_ms: float) -> None:
        """Update hourly statistics."""
        hour_key = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H')
        
        if hour_key not in self._hourly_stats:
            self._hourly_stats[hour_key] = {
                'total_checks': 0,
                'toxic_detected': 0,
                'avg_score': 0.0,
                'avg_duration': 0.0,
                'engine_breakdown': {}
            }
        
        stats = self._hourly_stats[hour_key]
        
        # Update running averages
        total = stats['total_checks']
        stats['avg_score'] = (stats['avg_score'] * total + score) / (total + 1)
        stats['avg_duration'] = (stats['avg_duration'] * total + duration_ms) / (total + 1)
        
        stats['total_checks'] += 1
        if result:
            stats['toxic_detected'] += 1
        
        # Update engine breakdown
        if engine_type not in stats['engine_breakdown']:
            stats['engine_breakdown'][engine_type] = 0
        stats['engine_breakdown'][engine_type] += 1
        
        # Limit hourly stats to last 24 hours
        if len(self._hourly_stats) > 24:
            oldest_hour = min(self._hourly_stats.keys())
            del self._hourly_stats[oldest_hour]
    
    def _to_prometheus_format(self) -> Dict[str, str]:
        """Convert metrics to Prometheus format."""
        metrics = {}
        
        # Toxicity metrics
        metrics['reflectpause_toxicity_checks_total'] = str(self.toxicity_metrics.total_checks)
        metrics['reflectpause_toxic_detected_total'] = str(self.toxicity_metrics.toxic_detected)
        metrics['reflectpause_toxicity_rate'] = str(self.toxicity_metrics.toxicity_rate / 100)
        metrics['reflectpause_cache_hits_total'] = str(self.toxicity_metrics.cache_hits)
        metrics['reflectpause_cache_hit_rate'] = str(self.toxicity_metrics.cache_hit_rate / 100)
        metrics['reflectpause_engine_errors_total'] = str(self.toxicity_metrics.engine_errors)
        
        # Performance metrics
        metrics['reflectpause_response_time_avg_ms'] = str(self.performance_metrics.avg_response_time)
        metrics['reflectpause_response_time_p95_ms'] = str(self.performance_metrics.p95_response_time)
        metrics['reflectpause_cache_speedup_factor'] = str(self.performance_metrics.cache_speedup)
        
        return metrics


# Global metrics collector instance
_global_collector: Optional[MetricsCollector] = None


def get_global_collector() -> MetricsCollector:
    """
    Get or create global metrics collector instance.
    
    Returns:
        Global MetricsCollector instance
    """
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector


def reset_global_metrics() -> None:
    """Reset the global metrics collector."""
    global _global_collector
    if _global_collector is not None:
        _global_collector.reset_metrics()