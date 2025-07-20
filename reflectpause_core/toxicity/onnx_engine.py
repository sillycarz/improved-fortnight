"""
ONNX-based toxicity detection engine for on-device inference.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    import numpy as np
    import onnxruntime as ort
except ImportError:
    # Graceful degradation if ONNX dependencies not available
    np = None
    ort = None

from .engine import ToxicityEngine, registry

logger = logging.getLogger(__name__)


class ONNXEngine(ToxicityEngine):
    """ONNX-based toxicity detection engine for on-device inference."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize ONNX engine.
        
        Args:
            config: Configuration dictionary with optional keys:
                - model_path: Path to ONNX model file
                - max_sequence_length: Maximum token sequence length
                - batch_size: Batch size for processing
        """
        super().__init__(config)
        
        config = config or {}
        self.model_path = config.get('model_path', 'models/detoxify_base_onnx.bin')
        self.max_sequence_length = config.get('max_sequence_length', 512)
        self.batch_size = config.get('batch_size', 1)
        
        self.session: Optional[ort.InferenceSession] = None
        self.input_name: Optional[str] = None
        self.output_name: Optional[str] = None
        
        # Simple tokenization (placeholder - real implementation would use proper tokenizer)
        self.vocab_size = config.get('vocab_size', 30000)
        
    def initialize(self) -> None:
        """
        Initialize the ONNX model and session.
        
        Raises:
            RuntimeError: If ONNX runtime is not available or model loading fails
        """
        if ort is None:
            raise RuntimeError("ONNX Runtime not available. Install with: pip install onnxruntime")
        
        if np is None:
            raise RuntimeError("NumPy not available. Install with: pip install numpy")
        
        try:
            model_path = Path(self.model_path)
            
            if not model_path.exists():
                logger.warning(f"ONNX model not found at {model_path}. Using mock implementation.")
                self.session = None
                self.is_initialized = True
                return
            
            # Create ONNX runtime session
            self.session = ort.InferenceSession(
                str(model_path),
                providers=['CPUExecutionProvider']  # Use CPU by default
            )
            
            # Get input/output names
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            
            logger.info(f"ONNX model loaded: {model_path}")
            logger.info(f"Input: {self.input_name}, Output: {self.output_name}")
            
            self.is_initialized = True
            
        except Exception as e:
            self._record_error(e)
            raise RuntimeError(f"Failed to initialize ONNX engine: {e}")
    
    def analyze(self, text: str) -> float:
        """
        Analyze text for toxicity using ONNX model.
        
        Args:
            text: Text to analyze
            
        Returns:
            Toxicity score between 0.0 and 1.0
            
        Raises:
            ValueError: If text is invalid
            RuntimeError: If analysis fails
        """
        self._validate_text(text)
        
        if not self.is_initialized:
            self.initialize()
        
        try:
            # If no model available, use simple heuristic
            if self.session is None:
                return self._simple_heuristic_check(text)
            
            # Tokenize text (simplified implementation)
            token_ids = self._tokenize(text)
            
            # Pad/truncate to max sequence length
            if len(token_ids) > self.max_sequence_length:
                token_ids = token_ids[:self.max_sequence_length]
            else:
                token_ids.extend([0] * (self.max_sequence_length - len(token_ids)))
            
            # Convert to numpy array
            input_ids = np.array([token_ids], dtype=np.int64)
            
            # Run inference
            outputs = self.session.run(
                [self.output_name],
                {self.input_name: input_ids}
            )
            
            # Extract toxicity score (assuming single output)
            score = float(outputs[0][0])
            
            # Ensure score is in [0, 1] range
            score = max(0.0, min(1.0, score))
            
            logger.debug(f"ONNX toxicity score: {score:.3f} for text length {len(text)}")
            return score
            
        except Exception as e:
            self._record_error(e)
            logger.warning(f"ONNX analysis failed, using fallback: {e}")
            return self._simple_heuristic_check(text)
    
    def analyze_batch(self, texts: List[str]) -> List[float]:
        """
        Analyze multiple texts for toxicity.
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            List of toxicity scores
        """
        if not self.supports_batch or self.session is None:
            return super().analyze_batch(texts)
        
        try:
            # Process in batches
            results = []
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i:i + self.batch_size]
                batch_scores = self._analyze_batch_internal(batch)
                results.extend(batch_scores)
            
            return results
            
        except Exception as e:
            self._record_error(e)
            logger.warning(f"Batch analysis failed, using individual analysis: {e}")
            return super().analyze_batch(texts)
    
    def _analyze_batch_internal(self, batch_texts: List[str]) -> List[float]:
        """Internal batch analysis implementation."""
        # Tokenize all texts
        batch_token_ids = []
        for text in batch_texts:
            self._validate_text(text)
            token_ids = self._tokenize(text)
            
            # Pad/truncate
            if len(token_ids) > self.max_sequence_length:
                token_ids = token_ids[:self.max_sequence_length]
            else:
                token_ids.extend([0] * (self.max_sequence_length - len(token_ids)))
            
            batch_token_ids.append(token_ids)
        
        # Convert to numpy array
        input_ids = np.array(batch_token_ids, dtype=np.int64)
        
        # Run batch inference
        outputs = self.session.run(
            [self.output_name],
            {self.input_name: input_ids}
        )
        
        # Extract scores
        scores = [max(0.0, min(1.0, float(score))) for score in outputs[0]]
        return scores
    
    def _tokenize(self, text: str) -> List[int]:
        """
        Simple tokenization (placeholder implementation).
        
        In a real implementation, this would use a proper tokenizer
        that matches the one used to train the model.
        """
        # Simple word-based tokenization
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Convert words to token IDs (simple hash-based approach)
        token_ids = []
        for word in words:
            # Simple hash to token ID
            token_id = hash(word) % self.vocab_size
            token_ids.append(abs(token_id))
        
        return token_ids
    
    def _simple_heuristic_check(self, text: str) -> float:
        """
        Simple heuristic-based toxicity check as fallback.
        
        This is used when ONNX model is not available.
        Enhanced with pattern matching and context awareness.
        """
        text_lower = text.lower()
        
        # Enhanced keyword categories with different weights
        toxic_keywords = {
            'high': ['hate', 'kill', 'die', 'threat', 'murder', 'violence'],
            'medium': ['stupid', 'idiot', 'awful', 'terrible', 'worst', 'pathetic'],
            'low': ['suck', 'fail', 'loser', 'annoying', 'dumb']
        }
        
        # Count toxic keywords with weights
        score = 0.0
        total_words = len(text.split())
        
        if total_words == 0:
            return 0.0
        
        # Weight keywords by severity
        for severity, keywords in toxic_keywords.items():
            weight = {'high': 0.8, 'medium': 0.5, 'low': 0.2}[severity]
            count = sum(1 for keyword in keywords if keyword in text_lower)
            score += (count / total_words) * weight
        
        # Cap at 1.0 and apply smoothing
        score = min(1.0, score * 2.0)  # Amplify for better sensitivity
        
        logger.debug(f"Heuristic toxicity score: {score:.3f} for {total_words} words")
        return score
    
    def cleanup(self) -> None:
        """Clean up ONNX session resources."""
        if self.session:
            # ONNX Runtime sessions are automatically cleaned up
            self.session = None
        self.is_initialized = False
        logger.debug("ONNX engine cleaned up")
    
    @property
    def engine_type(self) -> str:
        """Return engine type identifier."""
        return "onnx"
    
    @property
    def supports_batch(self) -> bool:
        """Return True if engine supports batch processing."""
        return True


# Register the ONNX engine as default
if ort is not None and np is not None:
    registry.register("onnx", ONNXEngine, is_default=True)
    logger.info("ONNX engine registered as default")
else:
    logger.warning("ONNX dependencies not available - engine not registered")