"""
Tests for decision logging module.
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from reflectpause_core.logging.decision_logger import (
    DecisionLogger, DecisionType, log_decision, 
    get_decision_stats, set_log_file
)


class TestDecisionType:
    """Tests for DecisionType enum."""
    
    def test_decision_type_values(self):
        """Test that DecisionType has expected values."""
        assert DecisionType.CONTINUED_SENDING.value == "continued_sending"
        assert DecisionType.EDITED_MESSAGE.value == "edited_message"
        assert DecisionType.CANCELLED_MESSAGE.value == "cancelled_message"
        assert DecisionType.PROMPT_VIEWED.value == "prompt_viewed"
        assert DecisionType.PROMPT_IGNORED.value == "prompt_ignored"


class TestDecisionLogger:
    """Tests for DecisionLogger class."""
    
    def test_logger_initialization_with_custom_file(self):
        """Test logger initialization with custom file path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test_decisions.jsonl"
            
            logger = DecisionLogger(str(log_file))
            
            assert logger.log_file == log_file
            assert logger.log_file.parent.exists()
    
    def test_logger_initialization_with_default_file(self):
        """Test logger initialization with default file path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = Path(temp_dir)
                
                logger = DecisionLogger()
                
                expected_path = Path(temp_dir) / ".reflectpause" / "decisions.jsonl"
                assert logger.log_file == expected_path
                assert logger.log_file.parent.exists()
    
    def test_log_decision_creates_valid_entry(self):
        """Test that log_decision creates a valid log entry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.jsonl"
            logger = DecisionLogger(str(log_file))
            
            logger.log_decision(DecisionType.CONTINUED_SENDING)
            
            assert log_file.exists()
            with open(log_file, 'r', encoding='utf-8') as f:
                line = f.readline().strip()
                entry = json.loads(line)
                
                assert "hash" in entry
                assert entry["decision"] == "continued_sending"
                assert "timestamp" in entry
                assert "date" in entry
                assert "hour" in entry
    
    def test_log_decision_with_metadata(self):
        """Test logging decision with metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.jsonl"
            logger = DecisionLogger(str(log_file))
            
            metadata = {
                "user_id": "12345",
                "message_length": 50,
                "toxicity_score": 0.8,
                "locale": "en"
            }
            
            logger.log_decision(DecisionType.EDITED_MESSAGE, metadata)
            
            with open(log_file, 'r', encoding='utf-8') as f:
                entry = json.loads(f.readline())
                
                assert "metadata" in entry
                assert "user_id_hash" in entry["metadata"]
                assert entry["metadata"]["message_length"] == 50
                assert entry["metadata"]["toxicity_score"] == 0.8
                assert entry["metadata"]["locale"] == "en"
    
    def test_log_decision_with_invalid_type_raises_error(self):
        """Test that invalid decision type raises ValueError."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.jsonl"
            logger = DecisionLogger(str(log_file))
            
            with pytest.raises(ValueError, match="Invalid decision type"):
                logger.log_decision("invalid_decision")
    
    def test_anonymize_metadata(self):
        """Test metadata anonymization."""
        logger = DecisionLogger()
        
        metadata = {
            "user_id": "sensitive123",
            "username": "testuser",
            "message_text": "This is a test message",
            "message_length": 25,
            "toxicity_score": 0.5,
            "locale": "en",
            "unknown_field": "should_be_ignored"
        }
        
        anonymized = logger._anonymize_metadata(metadata)
        
        # Sensitive fields should be hashed
        assert "user_id_hash" in anonymized
        assert "username_hash" in anonymized
        assert "user_id" not in anonymized
        assert "username" not in anonymized
        
        # Non-sensitive fields should be preserved
        assert anonymized["message_length"] == 25
        assert anonymized["toxicity_score"] == 0.5
        assert anonymized["locale"] == "en"
        
        # Message text should only preserve length
        assert "message_text" not in anonymized
        assert anonymized["message_length"] == 25
        
        # Unknown fields should be ignored
        assert "unknown_field" not in anonymized
    
    def test_get_stats_with_no_log_file(self):
        """Test get_stats when log file doesn't exist."""
        logger = DecisionLogger("/nonexistent/path/decisions.jsonl")
        
        stats = logger.get_stats()
        
        assert stats["total_entries"] == 0
        assert stats["decisions"] == {}
    
    def test_get_stats_with_log_entries(self):
        """Test get_stats with existing log entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.jsonl"
            logger = DecisionLogger(str(log_file))
            
            # Create some log entries
            logger.log_decision(DecisionType.CONTINUED_SENDING)
            logger.log_decision(DecisionType.EDITED_MESSAGE)
            logger.log_decision(DecisionType.CONTINUED_SENDING)
            
            stats = logger.get_stats()
            
            assert stats["total_entries"] == 3
            assert stats["decisions"]["continued_sending"] == 2
            assert stats["decisions"]["edited_message"] == 1
            assert "by_date" in stats
            assert "by_hour" in stats
    
    def test_get_stats_filters_by_date(self):
        """Test that get_stats filters entries by date range."""
        from datetime import datetime, date, timedelta, timezone
        
        # Use real datetime for calculations
        mock_now = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.jsonl"
            
            # Create entries with different dates
            old_entry = {
                "hash": "abc123",
                "decision": "continued_sending",
                "timestamp": "2023-05-01T12:00:00+00:00",
                "date": "2023-05-01",
                "hour": 12
            }
            
            recent_entry = {
                "hash": "def456",
                "decision": "edited_message",
                "timestamp": "2023-06-10T12:00:00+00:00",
                "date": "2023-06-10",
                "hour": 12
            }
            
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(json.dumps(old_entry) + '\n')
                f.write(json.dumps(recent_entry) + '\n')
            
            logger = DecisionLogger(str(log_file))
            # Temporarily patch datetime for consistent testing
            with patch('reflectpause_core.logging.decision_logger.datetime') as mock_dt:
                mock_dt.now.return_value = mock_now
                mock_dt.timedelta = timedelta
                
                stats = logger.get_stats(days=7)  # Only last 7 days
                
                # Should only include recent entry
                assert stats["total_entries"] == 1
                assert "edited_message" in stats["decisions"]
                assert "continued_sending" not in stats["decisions"]


class TestModuleFunctions:
    """Tests for module-level functions."""
    
    @patch('reflectpause_core.logging.decision_logger._decision_logger')
    def test_log_decision_function(self, mock_logger):
        """Test module-level log_decision function."""
        decision = DecisionType.PROMPT_VIEWED
        metadata = {"test": "data"}
        
        log_decision(decision, metadata)
        
        mock_logger.log_decision.assert_called_once_with(decision, metadata)
    
    @patch('reflectpause_core.logging.decision_logger._decision_logger')
    def test_get_decision_stats_function(self, mock_logger):
        """Test module-level get_decision_stats function."""
        mock_logger.get_stats.return_value = {"test": "stats"}
        
        result = get_decision_stats(7)
        
        mock_logger.get_stats.assert_called_once_with(7)
        assert result == {"test": "stats"}
    
    def test_set_log_file_function(self):
        """Test module-level set_log_file function."""
        import reflectpause_core.logging.decision_logger as module
        
        old_logger = module._decision_logger
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "decisions.jsonl"
            set_log_file(str(test_path))
            
            # Verify new logger was created
            assert module._decision_logger is not old_logger
            assert module._decision_logger.log_file == test_path