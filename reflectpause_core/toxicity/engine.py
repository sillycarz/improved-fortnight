"""
Base classes for toxicity detection engine strategy pattern.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ToxicityEngine(ABC):
    """Abstract base class for toxicity detection engines."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize toxicity engine.
        
        Args:
            config: Engine-specific configuration parameters
        """
        self.config = config or {}
        self.is_initialized = False
        self._last_error: Optional[Exception] = None
    
    @abstractmethod
    def analyze(self, text: str) -> float:
        """
        Analyze text for toxicity.
        
        Args:
            text: Text to analyze
            
        Returns:
            Toxicity score between 0.0 (not toxic) and 1.0 (highly toxic)
            
        Raises:
            ValueError: If text is invalid
            RuntimeError: If analysis fails
        """
        pass
    
    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the engine (load models, connect to APIs, etc.).
        
        Raises:
            RuntimeError: If initialization fails
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources (close connections, unload models, etc.)."""
        pass
    
    @property
    @abstractmethod
    def engine_type(self) -> str:
        """Return the engine type identifier."""
        pass
    
    @property
    @abstractmethod
    def supports_batch(self) -> bool:
        """Return True if engine supports batch processing."""
        pass
    
    def analyze_batch(self, texts: List[str]) -> List[float]:
        """
        Analyze multiple texts for toxicity.
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            List of toxicity scores corresponding to input texts
            
        Raises:
            NotImplementedError: If batch processing is not supported
            ValueError: If any text is invalid
            RuntimeError: If analysis fails
        """
        if not self.supports_batch:
            # Fall back to individual analysis
            return [self.analyze(text) for text in texts]
        
        raise NotImplementedError("Batch analysis not implemented")
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get engine health and status information.
        
        Returns:
            Dictionary with health status information
        """
        return {
            "engine_type": self.engine_type,
            "is_initialized": self.is_initialized,
            "last_error": str(self._last_error) if self._last_error else None,
            "config": {k: v for k, v in self.config.items() if not k.startswith('_')}
        }
    
    def _validate_text(self, text: str) -> None:
        """
        Validate input text.
        
        Args:
            text: Text to validate
            
        Raises:
            ValueError: If text is invalid
        """
        if not isinstance(text, str):
            raise ValueError(f"Text must be a string, got {type(text)}")
        
        if not text or not text.strip():
            raise ValueError("Text cannot be empty or whitespace-only")
        
        max_length = self.config.get('max_text_length', 10000)
        if len(text) > max_length:
            raise ValueError(f"Text length ({len(text)}) exceeds maximum ({max_length})")
    
    def _record_error(self, error: Exception) -> None:
        """Record the last error for health monitoring."""
        self._last_error = error
        logger.error(f"{self.engine_type} engine error: {error}")
    
    def __enter__(self):
        """Context manager entry."""
        if not self.is_initialized:
            self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


class EngineRegistry:
    """Registry for toxicity engine implementations."""
    
    def __init__(self):
        self._engines: Dict[str, type] = {}
        self._default_engine: Optional[str] = None
    
    def register(self, engine_type: str, engine_class: type, 
                 is_default: bool = False) -> None:
        """
        Register a toxicity engine implementation.
        
        Args:
            engine_type: Unique identifier for the engine
            engine_class: Engine class (must inherit from ToxicityEngine)
            is_default: Whether this should be the default engine
            
        Raises:
            ValueError: If engine_class is invalid
        """
        if not issubclass(engine_class, ToxicityEngine):
            raise ValueError(f"Engine class must inherit from ToxicityEngine")
        
        self._engines[engine_type] = engine_class
        
        if is_default or self._default_engine is None:
            self._default_engine = engine_type
        
        logger.info(f"Registered toxicity engine: {engine_type}")
    
    def create_engine(self, engine_type: Optional[str] = None, 
                      config: Optional[Dict[str, Any]] = None) -> ToxicityEngine:
        """
        Create an instance of the specified engine.
        
        Args:
            engine_type: Type of engine to create. If None, uses default.
            config: Configuration for the engine
            
        Returns:
            Initialized toxicity engine instance
            
        Raises:
            ValueError: If engine type is not registered
            RuntimeError: If engine creation fails
        """
        if engine_type is None:
            engine_type = self._default_engine
        
        if engine_type is None:
            raise ValueError("No default engine registered")
        
        if engine_type not in self._engines:
            available = list(self._engines.keys())
            raise ValueError(f"Unknown engine type '{engine_type}'. Available: {available}")
        
        try:
            engine_class = self._engines[engine_type]
            return engine_class(config)
        except Exception as e:
            raise RuntimeError(f"Failed to create {engine_type} engine: {e}")
    
    def get_available_engines(self) -> List[str]:
        """Get list of registered engine types."""
        return list(self._engines.keys())
    
    def get_default_engine(self) -> Optional[str]:
        """Get the default engine type."""
        return self._default_engine


# Global engine registry
registry = EngineRegistry()