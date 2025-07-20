"""
Tests for core module functions.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from reflectpause_core import check, generate_prompt, log_decision
from reflectpause_core.core import _toxicity_engine
from reflectpause_core.logging import DecisionType


class TestCheckFunction:
    """Tests for the check() function."""
    
    def test_check_with_empty_text_raises_error(self):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            check("")
        
        with pytest.raises(ValueError, match="Text cannot be empty"):
            check("   ")
    
    def test_check_with_invalid_threshold_raises_error(self):
        """Test that invalid threshold raises ValueError."""
        with pytest.raises(ValueError, match="Threshold must be between 0.0 and 1.0"):
            check("test", threshold=-0.1)
        
        with pytest.raises(ValueError, match="Threshold must be between 0.0 and 1.0"):
            check("test", threshold=1.5)
    
    def test_check_with_always_prompt_returns_true(self):
        """Test that always_prompt=True always returns True."""
        result = check("Hello world", always_prompt=True)
        assert result is True
    
    @patch('reflectpause_core.core.ONNXEngine')
    def test_check_initializes_engine_on_first_call(self, mock_onnx_engine):
        """Test that toxicity engine is initialized on first call."""
        mock_engine_instance = Mock()
        mock_engine_instance.analyze.return_value = 0.3
        mock_onnx_engine.return_value = mock_engine_instance
        
        # Clear global engine
        import reflectpause_core.core
        reflectpause_core.core._toxicity_engine = None
        
        result = check("test message", threshold=0.5)
        
        mock_onnx_engine.assert_called_once()
        mock_engine_instance.analyze.assert_called_once_with("test message")
        assert result is False  # 0.3 < 0.5
    
    @patch('reflectpause_core.core.ONNXEngine')
    def test_check_returns_true_when_score_exceeds_threshold(self, mock_onnx_engine):
        """Test that check returns True when toxicity exceeds threshold."""
        mock_engine_instance = Mock()
        mock_engine_instance.analyze.return_value = 0.8
        mock_onnx_engine.return_value = mock_engine_instance
        
        import reflectpause_core.core
        reflectpause_core.core._toxicity_engine = None
        
        result = check("toxic message", threshold=0.5)
        assert result is True  # 0.8 > 0.5
    
    @patch('reflectpause_core.core.ONNXEngine')
    def test_check_handles_engine_failure(self, mock_onnx_engine):
        """Test that check handles engine initialization failure."""
        mock_onnx_engine.side_effect = Exception("Engine failed")
        
        import reflectpause_core.core
        reflectpause_core.core._toxicity_engine = None
        
        with pytest.raises(RuntimeError, match="Failed to analyze text"):
            check("test message")


class TestGeneratePromptFunction:
    """Tests for the generate_prompt() function."""
    
    @patch('reflectpause_core.core._generate_prompt')
    def test_generate_prompt_calls_internal_function(self, mock_generate):
        """Test that generate_prompt calls internal function correctly."""
        from reflectpause_core.prompts.generator import PromptData
        
        expected_prompt = PromptData(
            title="Test Title",
            question="Test Question?",
            reflection_prompt="Think about it",
            continue_text="Continue",
            cancel_text="Cancel",
            locale="en"
        )
        mock_generate.return_value = expected_prompt
        
        result = generate_prompt("en")
        
        mock_generate.assert_called_once_with("en")
        assert result == expected_prompt
    
    @patch('reflectpause_core.core._generate_prompt')
    def test_generate_prompt_handles_errors(self, mock_generate):
        """Test that generate_prompt handles errors properly."""
        mock_generate.side_effect = Exception("Generation failed")
        
        with pytest.raises(RuntimeError, match="Failed to generate prompt"):
            generate_prompt("invalid")


class TestLogDecisionFunction:
    """Tests for the log_decision() function."""
    
    @patch('reflectpause_core.core._log_decision')
    def test_log_decision_calls_internal_function(self, mock_log):
        """Test that log_decision calls internal function correctly."""
        decision = DecisionType.CONTINUED_SENDING
        
        log_decision(decision)
        
        mock_log.assert_called_once_with(decision)
    
    @patch('reflectpause_core.core._log_decision')
    def test_log_decision_handles_errors(self, mock_log):
        """Test that log_decision handles errors properly."""
        mock_log.side_effect = Exception("Logging failed")
        
        with pytest.raises(RuntimeError, match="Failed to log decision"):
            log_decision(DecisionType.CONTINUED_SENDING)


class TestLoggingConfiguration:
    """Tests for logging configuration."""
    
    def test_logging_is_configured(self):
        """Test that logging is properly configured."""
        import reflectpause_core.core
        
        logger = reflectpause_core.core.logger
        assert logger.level == 10  # DEBUG level or INFO level
        assert len(logger.handlers) > 0