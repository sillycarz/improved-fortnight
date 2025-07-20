"""
Tests for toxicity detection engines.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from reflectpause_core.toxicity.engine import ToxicityEngine, EngineRegistry
from reflectpause_core.toxicity.onnx_engine import ONNXEngine
from reflectpause_core.toxicity.perspective_api import PerspectiveAPIEngine


class MockEngine(ToxicityEngine):
    """Mock engine for testing base class."""
    
    def analyze(self, text: str) -> float:
        self._validate_text(text)
        return 0.5
    
    def initialize(self) -> None:
        self.is_initialized = True
    
    def cleanup(self) -> None:
        self.is_initialized = False
    
    @property
    def engine_type(self) -> str:
        return "mock"
    
    @property
    def supports_batch(self) -> bool:
        return False


class TestToxicityEngine:
    """Tests for ToxicityEngine base class."""
    
    def test_engine_initialization(self):
        """Test engine initialization with config."""
        config = {"test_param": "test_value"}
        engine = MockEngine(config)
        
        assert engine.config == config
        assert not engine.is_initialized
        assert engine._last_error is None
    
    def test_validate_text_with_valid_input(self):
        """Test text validation with valid input."""
        engine = MockEngine()
        
        # Should not raise exception
        engine._validate_text("Valid text")
        engine._validate_text("Another valid text with numbers 123")
    
    def test_validate_text_with_invalid_input(self):
        """Test text validation with invalid input."""
        engine = MockEngine()
        
        with pytest.raises(ValueError, match="Text must be a string"):
            engine._validate_text(123)
        
        with pytest.raises(ValueError, match="Text cannot be empty"):
            engine._validate_text("")
        
        with pytest.raises(ValueError, match="Text cannot be empty"):
            engine._validate_text("   ")
    
    def test_validate_text_with_max_length(self):
        """Test text validation with maximum length constraint."""
        config = {"max_text_length": 10}
        engine = MockEngine(config)
        
        with pytest.raises(ValueError, match="Text length .* exceeds maximum"):
            engine._validate_text("This text is definitely longer than 10 characters")
    
    def test_analyze_batch_fallback(self):
        """Test batch analysis fallback for non-batch engines."""
        engine = MockEngine()
        
        texts = ["text1", "text2", "text3"]
        results = engine.analyze_batch(texts)
        
        assert len(results) == 3
        assert all(score == 0.5 for score in results)
    
    def test_get_health_status(self):
        """Test health status reporting."""
        config = {"param1": "value1", "_private": "hidden"}
        engine = MockEngine(config)
        
        status = engine.get_health_status()
        
        assert status["engine_type"] == "mock"
        assert status["is_initialized"] is False
        assert status["last_error"] is None
        assert status["config"]["param1"] == "value1"
        assert "_private" not in status["config"]
    
    def test_record_error(self):
        """Test error recording."""
        engine = MockEngine()
        test_error = Exception("Test error")
        
        engine._record_error(test_error)
        
        assert engine._last_error == test_error
    
    def test_context_manager(self):
        """Test context manager functionality."""
        engine = MockEngine()
        
        with engine:
            assert engine.is_initialized
        
        assert not engine.is_initialized


class TestEngineRegistry:
    """Tests for EngineRegistry class."""
    
    def test_register_engine(self):
        """Test engine registration."""
        registry = EngineRegistry()
        
        registry.register("test", MockEngine)
        
        assert "test" in registry.get_available_engines()
        assert registry.get_default_engine() == "test"
    
    def test_register_engine_with_default(self):
        """Test engine registration with default flag."""
        registry = EngineRegistry()
        
        registry.register("engine1", MockEngine)
        registry.register("engine2", MockEngine, is_default=True)
        
        assert registry.get_default_engine() == "engine2"
    
    def test_register_invalid_engine_raises_error(self):
        """Test that registering invalid engine raises error."""
        registry = EngineRegistry()
        
        with pytest.raises(ValueError, match="Engine class must inherit from ToxicityEngine"):
            registry.register("invalid", str)
    
    def test_create_engine_with_type(self):
        """Test creating engine with specific type."""
        registry = EngineRegistry()
        registry.register("test", MockEngine)
        
        engine = registry.create_engine("test")
        
        assert isinstance(engine, MockEngine)
        assert engine.engine_type == "mock"
    
    def test_create_engine_with_default(self):
        """Test creating engine with default type."""
        registry = EngineRegistry()
        registry.register("test", MockEngine, is_default=True)
        
        engine = registry.create_engine()
        
        assert isinstance(engine, MockEngine)
    
    def test_create_engine_with_unknown_type_raises_error(self):
        """Test that creating unknown engine type raises error."""
        registry = EngineRegistry()
        
        with pytest.raises(ValueError, match="Unknown engine type"):
            registry.create_engine("unknown")
    
    def test_create_engine_with_no_default_raises_error(self):
        """Test that creating engine with no default raises error."""
        registry = EngineRegistry()
        
        with pytest.raises(ValueError, match="No default engine registered"):
            registry.create_engine()


class TestONNXEngine:
    """Tests for ONNXEngine class."""
    
    def test_onnx_engine_initialization(self):
        """Test ONNX engine initialization."""
        config = {
            "model_path": "test/path/model.onnx",
            "max_sequence_length": 256,
            "batch_size": 4
        }
        
        engine = ONNXEngine(config)
        
        assert engine.model_path == "test/path/model.onnx"
        assert engine.max_sequence_length == 256
        assert engine.batch_size == 4
        assert engine.engine_type == "onnx"
        assert engine.supports_batch is True
    
    @patch('reflectpause_core.toxicity.onnx_engine.ort', None)
    def test_onnx_engine_without_runtime_raises_error(self):
        """Test ONNX engine raises error when runtime not available."""
        engine = ONNXEngine()
        
        with pytest.raises(RuntimeError, match="ONNX Runtime not available"):
            engine.initialize()
    
    @patch('reflectpause_core.toxicity.onnx_engine.ort')
    @patch('reflectpause_core.toxicity.onnx_engine.Path.exists')
    def test_onnx_engine_with_missing_model_uses_mock(self, mock_exists, mock_ort):
        """Test ONNX engine uses mock implementation when model missing."""
        mock_exists.return_value = False
        
        engine = ONNXEngine()
        engine.initialize()
        
        assert engine.is_initialized
        assert engine.session is None
    
    def test_onnx_engine_simple_heuristic_check(self):
        """Test ONNX engine simple heuristic fallback."""
        engine = ONNXEngine()
        
        # Test with toxic keywords
        toxic_score = engine._simple_heuristic_check("You are stupid and awful")
        assert toxic_score > 0
        
        # Test with non-toxic text
        clean_score = engine._simple_heuristic_check("Hello, how are you today?")
        assert clean_score == 0
    
    def test_onnx_tokenization(self):
        """Test ONNX tokenization."""
        engine = ONNXEngine()
        
        tokens = engine._tokenize("Hello world test")
        
        assert isinstance(tokens, list)
        assert len(tokens) == 3
        assert all(isinstance(token, int) for token in tokens)


class TestPerspectiveAPIEngine:
    """Tests for PerspectiveAPIEngine class."""
    
    def test_perspective_engine_initialization(self):
        """Test Perspective API engine initialization."""
        config = {
            "api_key": "test-api-key",
            "timeout": 15,
            "rate_limit_delay": 0.2
        }
        
        engine = PerspectiveAPIEngine(config)
        
        assert engine.api_key == "test-api-key"
        assert engine.timeout == 15
        assert engine.rate_limit_delay == 0.2
        assert engine.engine_type == "perspective_api"
        assert engine.supports_batch is False
    
    @patch('reflectpause_core.toxicity.perspective_api.requests', None)
    def test_perspective_engine_without_requests_raises_error(self):
        """Test Perspective API engine raises error when requests not available."""
        engine = PerspectiveAPIEngine({"api_key": "test"})
        
        with pytest.raises(RuntimeError, match="Requests library not available"):
            engine.initialize()
    
    def test_perspective_engine_without_api_key_raises_error(self):
        """Test Perspective API engine raises error when API key missing."""
        engine = PerspectiveAPIEngine({})
        
        with pytest.raises(RuntimeError, match="Perspective API key required"):
            engine.initialize()
    
    @patch('reflectpause_core.toxicity.perspective_api.requests')
    def test_perspective_engine_successful_request(self, mock_requests):
        """Test Perspective API engine successful request."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "attributeScores": {
                "TOXICITY": {
                    "summaryScore": {"value": 0.8}
                }
            }
        }
        mock_requests.post.return_value = mock_response
        
        engine = PerspectiveAPIEngine({"api_key": "test"})
        engine.is_initialized = True
        
        score = engine.analyze("Test toxic message")
        
        assert score == 0.8
        mock_requests.post.assert_called_once()
    
    @patch('reflectpause_core.toxicity.perspective_api.requests')
    def test_perspective_engine_rate_limit_response(self, mock_requests):
        """Test Perspective API engine handles rate limit."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_requests.post.return_value = mock_response
        
        engine = PerspectiveAPIEngine({"api_key": "test"})
        engine.is_initialized = True
        
        # Rate limit returns None, which should trigger warning and return 0.0
        score = engine.analyze("Test message")
        assert score == 0.0
    
    def test_perspective_engine_extract_score(self):
        """Test score extraction from API response."""
        engine = PerspectiveAPIEngine({"api_key": "test"})
        
        response_data = {
            "attributeScores": {
                "TOXICITY": {
                    "summaryScore": {"value": 0.75}
                }
            }
        }
        
        score = engine._extract_score(response_data, "TOXICITY")
        assert score == 0.75
    
    def test_perspective_engine_extract_score_missing_attribute(self):
        """Test score extraction with missing attribute."""
        engine = PerspectiveAPIEngine({"api_key": "test"})
        
        response_data = {"attributeScores": {}}
        
        score = engine._extract_score(response_data, "TOXICITY")
        assert score == 0.0