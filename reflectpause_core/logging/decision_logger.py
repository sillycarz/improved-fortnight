"""
Anonymized decision logging for analytics and insights.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DecisionType(Enum):
    """Types of user decisions to track."""
    
    CONTINUED_SENDING = "continued_sending"
    EDITED_MESSAGE = "edited_message"
    CANCELLED_MESSAGE = "cancelled_message"
    PROMPT_VIEWED = "prompt_viewed"
    PROMPT_IGNORED = "prompt_ignored"


class DecisionLogger:
    """Manages anonymized decision logging."""
    
    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize decision logger.
        
        Args:
            log_file: Path to log file. If None, uses default location.
        """
        if log_file is None:
            # Default to user's home directory or current directory
            home_dir = Path.home()
            log_dir = home_dir / ".reflectpause"
            log_dir.mkdir(exist_ok=True)
            self.log_file = log_dir / "decisions.jsonl"
        else:
            self.log_file = Path(log_file)
        
        # Ensure parent directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Decision logger initialized with file: {self.log_file}")
    
    def log_decision(self, decision: DecisionType, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an anonymized decision entry.
        
        Args:
            decision: The type of decision made
            metadata: Optional additional metadata (will be anonymized)
            
        Raises:
            ValueError: If decision is invalid
            RuntimeError: If logging fails
        """
        if not isinstance(decision, DecisionType):
            raise ValueError(f"Invalid decision type: {decision}")
        
        try:
            # Create anonymized entry
            timestamp = datetime.now(timezone.utc)
            
            # Create hash of timestamp + decision for anonymization
            hash_input = f"{timestamp.isoformat()}{decision.value}"
            entry_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
            
            entry = {
                "hash": entry_hash,
                "decision": decision.value,
                "timestamp": timestamp.isoformat(),
                "date": timestamp.date().isoformat(),
                "hour": timestamp.hour
            }
            
            # Add anonymized metadata if provided
            if metadata:
                entry["metadata"] = self._anonymize_metadata(metadata)
            
            # Append to log file (JSONL format)
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
            
            logger.debug(f"Logged decision: {decision.value} (hash: {entry_hash})")
            
        except Exception as e:
            logger.error(f"Failed to log decision: {e}")
            raise RuntimeError(f"Decision logging failed: {e}")
    
    def _anonymize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize metadata by removing/hashing sensitive information.
        
        Args:
            metadata: Raw metadata dictionary
            
        Returns:
            Anonymized metadata dictionary
        """
        anonymized = {}
        
        for key, value in metadata.items():
            if key in ['user_id', 'username', 'channel_id', 'guild_id']:
                # Hash sensitive IDs
                if value:
                    anonymized[f"{key}_hash"] = hashlib.sha256(str(value).encode()).hexdigest()[:8]
            elif key in ['message_length', 'toxicity_score', 'locale', 'engine_type']:
                # Keep non-sensitive metrics
                anonymized[key] = value
            elif key == 'message_text':
                # Only keep length, not content
                if value:
                    anonymized['message_length'] = len(str(value))
            else:
                logger.warning(f"Unknown metadata key '{key}' - skipping")
        
        return anonymized
    
    def get_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get anonymized decision statistics for the last N days.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with decision statistics
        """
        if not self.log_file.exists():
            return {"total_entries": 0, "decisions": {}}
        
        cutoff_date = (datetime.now(timezone.utc).date() - 
                      timedelta(days=days)).isoformat()
        
        stats = {
            "total_entries": 0,
            "decisions": {},
            "by_date": {},
            "by_hour": {}
        }
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    entry = json.loads(line)
                    entry_date = entry.get("date")
                    
                    # Skip entries older than cutoff
                    if entry_date and entry_date < cutoff_date:
                        continue
                    
                    stats["total_entries"] += 1
                    
                    # Count by decision type
                    decision = entry.get("decision", "unknown")
                    stats["decisions"][decision] = stats["decisions"].get(decision, 0) + 1
                    
                    # Count by date
                    if entry_date:
                        stats["by_date"][entry_date] = stats["by_date"].get(entry_date, 0) + 1
                    
                    # Count by hour
                    hour = entry.get("hour", 0)
                    stats["by_hour"][hour] = stats["by_hour"].get(hour, 0) + 1
            
        except Exception as e:
            logger.error(f"Failed to generate stats: {e}")
            stats["error"] = str(e)
        
        return stats


# Global logger instance
_decision_logger = DecisionLogger()


def log_decision(decision: DecisionType, metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    Log an anonymized decision entry.
    
    Args:
        decision: The type of decision made
        metadata: Optional additional metadata
    """
    _decision_logger.log_decision(decision, metadata)


def get_decision_stats(days: int = 30) -> Dict[str, Any]:
    """
    Get decision statistics for the last N days.
    
    Args:
        days: Number of days to analyze
        
    Returns:
        Dictionary with anonymized statistics
    """
    return _decision_logger.get_stats(days)


def set_log_file(file_path: str) -> None:
    """
    Set custom log file location.
    
    Args:
        file_path: Path to log file
    """
    global _decision_logger
    _decision_logger = DecisionLogger(file_path)