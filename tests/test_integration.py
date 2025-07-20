"""
Integration tests for end-to-end toxicity detection workflows.
"""

import unittest
import time
import tempfile
import os
from unittest.mock import patch, MagicMock

from reflectpause_core import check, generate_prompt, log_decision
from reflectpause_core.core import _toxicity_engine
from reflectpause_core.toxicity.onnx_engine import ONNXEngine
from reflectpause_core.toxicity.perspective_api import PerspectiveAPIEngine
from reflectpause_core.logging.decision_logger import DecisionType
from reflectpause_core.cache.toxicity_cache import get_global_cache, clear_global_cache


class IntegrationTestCase(unittest.TestCase):
    """Base class for integration tests with common setup."""
    
    def setUp(self):
        """Set up test environment."""
        # Clear global cache before each test
        clear_global_cache()
        
        # Reset global engine
        global _toxicity_engine
        from reflectpause_core import core
        core._toxicity_engine = None
    
    def tearDown(self):
        """Clean up after tests."""
        clear_global_cache()


class EndToEndWorkflowTests(IntegrationTestCase):
    """Test complete toxicity detection workflows."""
    
    def test_basic_toxicity_check_workflow(self):
        """Test basic toxicity check with caching."""
        test_text = "You are an idiot and I hate you"
        
        # First check - should analyze and cache
        start_time = time.perf_counter()
        result1 = check(test_text, threshold=0.5)
        duration1 = (time.perf_counter() - start_time) * 1000
        
        self.assertIsInstance(result1, bool)
        
        # Second check - should use cache
        start_time = time.perf_counter()
        result2 = check(test_text, threshold=0.5)
        duration2 = (time.perf_counter() - start_time) * 1000
        
        # Results should be identical
        self.assertEqual(result1, result2)
        
        # Second check should be faster (cached)
        self.assertLess(duration2, duration1)
        
        # Verify cache was used
        cache = get_global_cache()
        stats = cache.get_stats()
        self.assertGreater(stats['hits'], 0)
    
    def test_prompt_generation_workflow(self):
        """Test prompt generation workflow."""
        # Test English prompt
        prompt_en = generate_prompt("en")
        self.assertIsNotNone(prompt_en)
        self.assertIsNotNone(prompt_en.title)
        self.assertIsNotNone(prompt_en.question)
        self.assertIsNotNone(prompt_en.reflection_prompt)
        
        # Test Vietnamese prompt
        prompt_vi = generate_prompt("vi")
        self.assertIsNotNone(prompt_vi)
        self.assertIsNotNone(prompt_vi.title)
        self.assertIsNotNone(prompt_vi.question)
        self.assertIsNotNone(prompt_vi.reflection_prompt)
        
        # Questions should rotate
        prompt_en2 = generate_prompt("en")
        # May or may not be different due to rotation, but should be valid
        self.assertIsNotNone(prompt_en2.question)
    
    def test_decision_logging_workflow(self):
        """Test decision logging workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Override log file location for test
            log_file = os.path.join(temp_dir, "test_decisions.jsonl")
            
            with patch('reflectpause_core.logging.decision_logger._decision_logger', None):
                from reflectpause_core.logging.decision_logger import DecisionLogger
                test_logger = DecisionLogger(log_file)
                
                with patch('reflectpause_core.logging.decision_logger._decision_logger', test_logger):
                    # Log some decisions
                    log_decision(DecisionType.CONTINUED_SENDING)
                    log_decision(DecisionType.EDITED_MESSAGE)
                    log_decision(DecisionType.CANCELLED_MESSAGE)
                    
                    # Verify log file was created and has content
                    self.assertTrue(os.path.exists(log_file))
                    with open(log_file, 'r') as f:
                        content = f.read()
                        self.assertGreater(len(content), 0)
                        # Should have 3 lines (one per decision)
                        lines = content.strip().split('\n')
                        self.assertEqual(len(lines), 3)
    
    def test_complete_user_workflow(self):
        """Test complete user workflow: check -> prompt -> log."""
        test_text = "This is inappropriate content that should trigger a prompt"
        
        # Step 1: Check toxicity
        needs_prompt = check(test_text, threshold=0.3)
        
        if needs_prompt:
            # Step 2: Generate prompt
            prompt = generate_prompt("en")
            self.assertIsNotNone(prompt)
            
            # Step 3: User makes decision (simulate)
            user_decision = DecisionType.EDITED_MESSAGE  # User chose to edit
            
            # Step 4: Log decision
            with tempfile.TemporaryDirectory() as temp_dir:
                log_file = os.path.join(temp_dir, "test_workflow.jsonl")
                with patch('reflectpause_core.logging.decision_logger._decision_logger', None):
                    from reflectpause_core.logging.decision_logger import DecisionLogger
                    test_logger = DecisionLogger(log_file)
                    
                    with patch('reflectpause_core.logging.decision_logger._decision_logger', test_logger):
                        log_decision(user_decision)
                        
                        # Verify logging worked
                        self.assertTrue(os.path.exists(log_file))
    
    def test_performance_requirements(self):
        """Test that performance requirements are met."""
        test_text = "Test message for performance validation"
        
        # First run to initialize engine and cache miss
        check(test_text)
        
        # Measure cached performance (should be very fast)
        start_time = time.perf_counter()
        check(test_text)
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        # Should meet G1 latency requirement (≤ 50ms)
        self.assertLess(duration_ms, 50, 
                       f"Cached toxicity check took {duration_ms:.1f}ms, exceeds 50ms target")
    
    def test_error_handling_workflow(self):
        """Test error handling in complete workflow."""
        # Test invalid text
        with self.assertRaises(ValueError):
            check("")
        
        with self.assertRaises(ValueError):
            check(None)
        
        # Test invalid threshold
        with self.assertRaises(ValueError):
            check("test", threshold=1.5)
        
        # Test invalid locale (should fallback gracefully, not raise error)
        prompt = generate_prompt("invalid_locale")
        self.assertIsNotNone(prompt)  # Should fallback to English
        
        # Test invalid decision type
        with self.assertRaises(RuntimeError):
            log_decision("invalid_decision")


class MultiEngineIntegrationTests(IntegrationTestCase):
    """Test integration with multiple toxicity engines."""
    
    def test_onnx_engine_workflow(self):
        """Test workflow with ONNX engine."""
        with patch.object(ONNXEngine, 'analyze') as mock_analyze:
            mock_analyze.return_value = 0.8
            
            result = check("test toxic content", threshold=0.5)
            self.assertTrue(result)
            mock_analyze.assert_called_once()
    
    def test_perspective_api_workflow(self):
        """Test workflow with Perspective API engine."""
        # Mock the engine creation and analysis
        with patch('reflectpause_core.core._toxicity_engine', None):
            with patch('reflectpause_core.core.ONNXEngine') as mock_onnx:
                mock_engine = MagicMock()
                mock_engine.analyze.return_value = 0.3
                mock_engine.engine_type = "onnx"
                mock_onnx.return_value = mock_engine
                
                result = check("test content", threshold=0.5)
                self.assertFalse(result)
                mock_engine.analyze.assert_called_once()
    
    def test_engine_failure_handling(self):
        """Test handling of engine failures."""
        with patch.object(ONNXEngine, 'analyze') as mock_analyze:
            mock_analyze.side_effect = RuntimeError("Engine failed")
            
            with self.assertRaises(RuntimeError):
                check("test content")


class CacheIntegrationTests(IntegrationTestCase):
    """Test cache integration in workflows."""
    
    def test_cache_across_multiple_calls(self):
        """Test cache behavior across multiple toxicity checks."""
        texts = [
            "This is normal content",
            "This is toxic garbage content",
            "Another normal message"
        ]
        
        # First round - all cache misses
        results1 = [check(text) for text in texts]
        
        # Second round - all cache hits
        results2 = [check(text) for text in texts]
        
        # Results should be identical
        self.assertEqual(results1, results2)
        
        # Verify cache statistics
        cache = get_global_cache()
        stats = cache.get_stats()
        self.assertGreaterEqual(stats['hits'], 3)  # Second round should have hits
        self.assertGreaterEqual(stats['misses'], 3)  # First round should have misses
    
    def test_cache_invalidation(self):
        """Test cache invalidation scenarios."""
        test_text = "Test content for cache invalidation"
        
        # Initial check
        result1 = check(test_text)
        
        # Verify it's cached
        cache = get_global_cache()
        cached_score = cache.get(test_text, "onnx")
        self.assertIsNotNone(cached_score)
        
        # Invalidate cache
        cache.invalidate(test_text, "onnx")
        
        # Should be cache miss now
        cached_score = cache.get(test_text, "onnx")
        self.assertIsNone(cached_score)
    
    def test_cache_expiration(self):
        """Test cache TTL expiration."""
        from reflectpause_core.cache.toxicity_cache import ToxicityCache
        
        # Create new cache instance with very short TTL
        cache = ToxicityCache(max_size=100, ttl_seconds=1)
        
        test_text = "Test content for expiration"
        
        # Put item in cache
        cache.put(test_text, "onnx", 0.5)
        
        # Should be available immediately
        score = cache.get(test_text, "onnx")
        self.assertIsNotNone(score)
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired now
        score = cache.get(test_text, "onnx")
        self.assertIsNone(score)


class ConcurrencyIntegrationTests(IntegrationTestCase):
    """Test concurrent access scenarios."""
    
    def test_concurrent_toxicity_checks(self):
        """Test concurrent toxicity checks with caching."""
        import threading
        import concurrent.futures
        
        test_texts = [f"Test message {i}" for i in range(10)]
        results = {}
        
        def check_toxicity(text):
            return check(text, threshold=0.5)
        
        # Run concurrent checks
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_text = {
                executor.submit(check_toxicity, text): text 
                for text in test_texts
            }
            
            for future in concurrent.futures.as_completed(future_to_text):
                text = future_to_text[future]
                try:
                    result = future.result()
                    results[text] = result
                except Exception as exc:
                    self.fail(f"Text {text} generated an exception: {exc}")
        
        # All texts should have results
        self.assertEqual(len(results), len(test_texts))
        
        # Results should be deterministic when run again
        results2 = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_text = {
                executor.submit(check_toxicity, text): text 
                for text in test_texts
            }
            
            for future in concurrent.futures.as_completed(future_to_text):
                text = future_to_text[future]
                results2[text] = future.result()
        
        # Results should be identical
        self.assertEqual(results, results2)


if __name__ == '__main__':
    unittest.main()