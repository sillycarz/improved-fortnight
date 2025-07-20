"""
Accuracy tracking for toxicity detection engines.
"""

import hashlib
import json
import threading
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Types of user feedback for accuracy tracking."""
    CORRECT_POSITIVE = "correct_positive"    # Correctly flagged as toxic
    CORRECT_NEGATIVE = "correct_negative"    # Correctly flagged as non-toxic
    FALSE_POSITIVE = "false_positive"        # Incorrectly flagged as toxic
    FALSE_NEGATIVE = "false_negative"        # Missed toxic content


@dataclass
class AccuracyMetrics:
    """Metrics for toxicity detection accuracy."""
    true_positives: int = 0    # Correctly identified toxic content
    true_negatives: int = 0    # Correctly identified non-toxic content
    false_positives: int = 0   # Incorrectly flagged as toxic
    false_negatives: int = 0   # Missed toxic content
    
    @property
    def total_predictions(self) -> int:
        """Total number of predictions made."""
        return self.true_positives + self.true_negatives + self.false_positives + self.false_negatives
    
    @property
    def accuracy(self) -> float:
        """Overall accuracy percentage."""
        if self.total_predictions == 0:
            return 0.0
        return ((self.true_positives + self.true_negatives) / self.total_predictions) * 100
    
    @property
    def precision(self) -> float:
        """Precision for toxic content detection."""
        total_positive_predictions = self.true_positives + self.false_positives
        if total_positive_predictions == 0:
            return 0.0
        return (self.true_positives / total_positive_predictions) * 100
    
    @property
    def recall(self) -> float:
        """Recall for toxic content detection."""
        total_actual_positives = self.true_positives + self.false_negatives
        if total_actual_positives == 0:
            return 0.0
        return (self.true_positives / total_actual_positives) * 100
    
    @property
    def f1_score(self) -> float:
        """F1 score for toxic content detection."""
        if self.precision == 0 and self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)
    
    @property
    def false_positive_rate(self) -> float:
        """False positive rate percentage."""
        total_actual_negatives = self.true_negatives + self.false_positives
        if total_actual_negatives == 0:
            return 0.0
        return (self.false_positives / total_actual_negatives) * 100


class AccuracyTracker:
    """
    Thread-safe tracker for toxicity detection accuracy.
    
    Collects user feedback and ground truth data to measure
    engine performance and accuracy over time.
    """
    
    def __init__(self, storage_file: Optional[str] = None):
        """
        Initialize accuracy tracker.
        
        Args:
            storage_file: Optional file to persist accuracy data
        """
        self.storage_file = storage_file
        self._lock = threading.RLock()
        
        # Accuracy metrics by engine
        self._engine_metrics: Dict[str, AccuracyMetrics] = {}
        
        # Detailed feedback storage
        self._feedback_history: List[Dict] = []
        
        # Ground truth data for validation
        self._ground_truth: Dict[str, bool] = {}  # text_hash -> is_toxic
        
        # Confidence tracking
        self._confidence_buckets: Dict[str, List[Tuple[float, bool]]] = {}  # score_range -> [(score, actual)]
        
        # Load existing data if available
        self._load_data()
    
    def record_feedback(self, 
                       text: str,
                       predicted_toxic: bool,
                       actual_toxic: bool,
                       engine_type: str,
                       confidence_score: float = None) -> None:
        """
        Record user feedback for a toxicity prediction.
        
        Args:
            text: Original text that was analyzed
            predicted_toxic: What the engine predicted
            actual_toxic: What the actual result should be (ground truth)
            engine_type: Engine that made the prediction
            confidence_score: Confidence score from engine (0-1)
        """
        with self._lock:
            # Determine feedback type
            if predicted_toxic and actual_toxic:
                feedback_type = FeedbackType.CORRECT_POSITIVE
            elif not predicted_toxic and not actual_toxic:
                feedback_type = FeedbackType.CORRECT_NEGATIVE
            elif predicted_toxic and not actual_toxic:
                feedback_type = FeedbackType.FALSE_POSITIVE
            else:  # not predicted_toxic and actual_toxic
                feedback_type = FeedbackType.FALSE_NEGATIVE
            
            # Update engine metrics
            if engine_type not in self._engine_metrics:
                self._engine_metrics[engine_type] = AccuracyMetrics()
            
            metrics = self._engine_metrics[engine_type]
            
            if feedback_type == FeedbackType.CORRECT_POSITIVE:
                metrics.true_positives += 1
            elif feedback_type == FeedbackType.CORRECT_NEGATIVE:
                metrics.true_negatives += 1
            elif feedback_type == FeedbackType.FALSE_POSITIVE:
                metrics.false_positives += 1
            elif feedback_type == FeedbackType.FALSE_NEGATIVE:
                metrics.false_negatives += 1
            
            # Store feedback history
            feedback_record = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'text_hash': self._hash_text(text),
                'predicted_toxic': predicted_toxic,
                'actual_toxic': actual_toxic,
                'engine_type': engine_type,
                'feedback_type': feedback_type.value,
                'confidence_score': confidence_score
            }
            
            self._feedback_history.append(feedback_record)
            
            # Update ground truth
            text_hash = self._hash_text(text)
            self._ground_truth[text_hash] = actual_toxic
            
            # Update confidence tracking
            if confidence_score is not None:
                bucket = self._get_confidence_bucket(confidence_score)
                if bucket not in self._confidence_buckets:
                    self._confidence_buckets[bucket] = []
                self._confidence_buckets[bucket].append((confidence_score, actual_toxic))
            
            # Persist data
            self._save_data()
            
            logger.info(f"Recorded feedback: {feedback_type.value} for {engine_type} "
                       f"(predicted: {predicted_toxic}, actual: {actual_toxic})")
    
    def get_accuracy_metrics(self, engine_type: Optional[str] = None) -> Dict:
        """
        Get accuracy metrics for specified engine or all engines.
        
        Args:
            engine_type: Specific engine to get metrics for, or None for all
            
        Returns:
            Dictionary with accuracy metrics
        """
        with self._lock:
            if engine_type:
                if engine_type not in self._engine_metrics:
                    return {'error': f'No data for engine: {engine_type}'}
                
                metrics = self._engine_metrics[engine_type]
                return {
                    'engine_type': engine_type,
                    'total_predictions': metrics.total_predictions,
                    'accuracy': metrics.accuracy,
                    'precision': metrics.precision,
                    'recall': metrics.recall,
                    'f1_score': metrics.f1_score,
                    'false_positive_rate': metrics.false_positive_rate,
                    'confusion_matrix': {
                        'true_positives': metrics.true_positives,
                        'true_negatives': metrics.true_negatives,
                        'false_positives': metrics.false_positives,
                        'false_negatives': metrics.false_negatives
                    }
                }
            else:
                # Return metrics for all engines
                return {
                    engine: {
                        'total_predictions': metrics.total_predictions,
                        'accuracy': metrics.accuracy,
                        'precision': metrics.precision,
                        'recall': metrics.recall,
                        'f1_score': metrics.f1_score,
                        'false_positive_rate': metrics.false_positive_rate
                    }
                    for engine, metrics in self._engine_metrics.items()
                }
    
    def get_confidence_analysis(self) -> Dict:
        """
        Analyze accuracy by confidence score ranges.
        
        Returns:
            Dictionary with confidence-based accuracy analysis
        """
        with self._lock:
            analysis = {}
            
            for bucket, scores_and_actuals in self._confidence_buckets.items():
                if not scores_and_actuals:
                    continue
                
                total = len(scores_and_actuals)
                correct = sum(1 for score, actual in scores_and_actuals 
                             if (score > 0.5) == actual)
                
                avg_confidence = sum(score for score, _ in scores_and_actuals) / total
                
                analysis[bucket] = {
                    'total_predictions': total,
                    'accuracy': (correct / total) * 100,
                    'avg_confidence': avg_confidence
                }
            
            return analysis
    
    def get_feedback_summary(self, limit: int = 100) -> List[Dict]:
        """
        Get recent feedback history.
        
        Args:
            limit: Maximum number of feedback records to return
            
        Returns:
            List of recent feedback records
        """
        with self._lock:
            return self._feedback_history[-limit:] if self._feedback_history else []
    
    def validate_predictions(self, 
                           predictions: List[Tuple[str, bool, str, float]]) -> Dict:
        """
        Validate a batch of predictions against ground truth.
        
        Args:
            predictions: List of (text, predicted_toxic, engine_type, confidence) tuples
            
        Returns:
            Validation results with accuracy metrics
        """
        results = {
            'total_validated': 0,
            'matched_ground_truth': 0,
            'accuracy': 0.0,
            'details': []
        }
        
        with self._lock:
            for text, predicted_toxic, engine_type, confidence in predictions:
                text_hash = self._hash_text(text)
                
                if text_hash in self._ground_truth:
                    actual_toxic = self._ground_truth[text_hash]
                    is_correct = predicted_toxic == actual_toxic
                    
                    results['total_validated'] += 1
                    if is_correct:
                        results['matched_ground_truth'] += 1
                    
                    results['details'].append({
                        'text_hash': text_hash[:8] + '...',
                        'predicted': predicted_toxic,
                        'actual': actual_toxic,
                        'correct': is_correct,
                        'engine': engine_type,
                        'confidence': confidence
                    })
            
            if results['total_validated'] > 0:
                results['accuracy'] = (results['matched_ground_truth'] / 
                                     results['total_validated']) * 100
        
        return results
    
    def export_ground_truth(self) -> Dict[str, bool]:
        """Export ground truth data for external validation."""
        with self._lock:
            return self._ground_truth.copy()
    
    def import_ground_truth(self, ground_truth: Dict[str, bool]) -> int:
        """
        Import ground truth data from external source.
        
        Args:
            ground_truth: Dictionary mapping text hashes to toxicity labels
            
        Returns:
            Number of ground truth entries imported
        """
        with self._lock:
            imported = 0
            for text_hash, is_toxic in ground_truth.items():
                if text_hash not in self._ground_truth:
                    self._ground_truth[text_hash] = is_toxic
                    imported += 1
            
            self._save_data()
            return imported
    
    def reset_accuracy_data(self, engine_type: Optional[str] = None) -> None:
        """
        Reset accuracy data for specified engine or all engines.
        
        Args:
            engine_type: Specific engine to reset, or None for all
        """
        with self._lock:
            if engine_type:
                if engine_type in self._engine_metrics:
                    del self._engine_metrics[engine_type]
                # Remove feedback for specific engine
                self._feedback_history = [
                    record for record in self._feedback_history
                    if record.get('engine_type') != engine_type
                ]
            else:
                self._engine_metrics.clear()
                self._feedback_history.clear()
                self._ground_truth.clear()
                self._confidence_buckets.clear()
            
            self._save_data()
    
    def _hash_text(self, text: str) -> str:
        """Generate hash for text (for privacy)."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def _get_confidence_bucket(self, score: float) -> str:
        """Get confidence bucket for score."""
        if score < 0.2:
            return "0.0-0.2"
        elif score < 0.4:
            return "0.2-0.4"
        elif score < 0.6:
            return "0.4-0.6"
        elif score < 0.8:
            return "0.6-0.8"
        else:
            return "0.8-1.0"
    
    def _load_data(self) -> None:
        """Load accuracy data from storage file."""
        if not self.storage_file:
            return
        
        try:
            with open(self.storage_file, 'r') as f:
                data = json.load(f)
                
                # Load engine metrics
                for engine, metrics_data in data.get('engine_metrics', {}).items():
                    metrics = AccuracyMetrics()
                    metrics.true_positives = metrics_data.get('true_positives', 0)
                    metrics.true_negatives = metrics_data.get('true_negatives', 0)
                    metrics.false_positives = metrics_data.get('false_positives', 0)
                    metrics.false_negatives = metrics_data.get('false_negatives', 0)
                    self._engine_metrics[engine] = metrics
                
                # Load other data
                self._feedback_history = data.get('feedback_history', [])
                self._ground_truth = data.get('ground_truth', {})
                self._confidence_buckets = data.get('confidence_buckets', {})
                
                logger.info(f"Loaded accuracy data from {self.storage_file}")
                
        except FileNotFoundError:
            logger.info(f"No existing accuracy data file found at {self.storage_file}")
        except Exception as e:
            logger.error(f"Failed to load accuracy data: {e}")
    
    def _save_data(self) -> None:
        """Save accuracy data to storage file."""
        if not self.storage_file:
            return
        
        try:
            data = {
                'engine_metrics': {
                    engine: {
                        'true_positives': metrics.true_positives,
                        'true_negatives': metrics.true_negatives,
                        'false_positives': metrics.false_positives,
                        'false_negatives': metrics.false_negatives
                    }
                    for engine, metrics in self._engine_metrics.items()
                },
                'feedback_history': self._feedback_history,
                'ground_truth': self._ground_truth,
                'confidence_buckets': self._confidence_buckets
            }
            
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save accuracy data: {e}")


# Global accuracy tracker instance
_global_tracker: Optional[AccuracyTracker] = None


def get_global_tracker(storage_file: Optional[str] = None) -> AccuracyTracker:
    """
    Get or create global accuracy tracker instance.
    
    Args:
        storage_file: Storage file for persistence (only used on first call)
        
    Returns:
        Global AccuracyTracker instance
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = AccuracyTracker(storage_file)
    return _global_tracker