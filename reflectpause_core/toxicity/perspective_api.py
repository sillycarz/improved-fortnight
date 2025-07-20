"""
Google Perspective API-based toxicity detection engine.
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List

try:
    import requests
except ImportError:
    requests = None

from .engine import ToxicityEngine, registry

logger = logging.getLogger(__name__)


class PerspectiveAPIEngine(ToxicityEngine):
    """Google Perspective API-based toxicity detection engine."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Perspective API engine.
        
        Args:
            config: Configuration dictionary with required keys:
                - api_key: Google Perspective API key
                - timeout: Request timeout in seconds (default: 10)
                - rate_limit_delay: Delay between requests in seconds (default: 0.1)
                - threshold_attribute: Attribute to use for scoring (default: TOXICITY)
        """
        super().__init__(config)
        
        config = config or {}
        self.api_key = config.get('api_key')
        self.timeout = config.get('timeout', 10)
        self.rate_limit_delay = config.get('rate_limit_delay', 0.1)
        self.threshold_attribute = config.get('threshold_attribute', 'TOXICITY')
        
        self.base_url = "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze"
        self.last_request_time = 0
        
        # API attributes to request
        self.attributes = {
            'TOXICITY': {},
            'SEVERE_TOXICITY': {},
            'IDENTITY_ATTACK': {},
            'INSULT': {},
            'PROFANITY': {},
            'THREAT': {}
        }
    
    def initialize(self) -> None:
        """
        Initialize the Perspective API engine.
        
        Raises:
            RuntimeError: If API key is missing or requests library unavailable
        """
        if requests is None:
            raise RuntimeError("Requests library not available. Install with: pip install requests")
        
        if not self.api_key:
            raise RuntimeError(
                "Perspective API key required. Set 'api_key' in config or "
                "PERSPECTIVE_API_KEY environment variable"
            )
        
        # Test API connectivity
        try:
            test_response = self._make_request("Hello world", test_mode=True)
            if test_response:
                logger.info("Perspective API connection successful")
            else:
                logger.warning("Perspective API test failed - API may be unavailable")
        except Exception as e:
            logger.warning(f"Perspective API test failed: {e}")
        
        self.is_initialized = True
    
    def analyze(self, text: str) -> float:
        """
        Analyze text for toxicity using Perspective API.
        
        Args:
            text: Text to analyze
            
        Returns:
            Toxicity score between 0.0 and 1.0
            
        Raises:
            ValueError: If text is invalid
            RuntimeError: If API request fails
        """
        self._validate_text(text)
        
        if not self.is_initialized:
            self.initialize()
        
        try:
            # Rate limiting
            self._enforce_rate_limit()
            
            # Make API request
            response_data = self._make_request(text)
            
            if not response_data:
                logger.warning("Empty response from Perspective API")
                return 0.0
            
            # Extract toxicity score
            score = self._extract_score(response_data, self.threshold_attribute)
            
            logger.debug(f"Perspective API toxicity score: {score:.3f}")
            return score
            
        except Exception as e:
            self._record_error(e)
            logger.error(f"Perspective API analysis failed: {e}")
            # Return 0.0 for graceful degradation instead of raising
            return 0.0
    
    def analyze_batch(self, texts: List[str]) -> List[float]:
        """
        Analyze multiple texts (sequentially due to API limitations).
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            List of toxicity scores
        """
        # Perspective API doesn't support true batch requests
        # Process sequentially with rate limiting
        results = []
        
        for text in texts:
            try:
                score = self.analyze(text)
                results.append(score)
            except Exception as e:
                logger.warning(f"Failed to analyze text in batch: {e}")
                results.append(0.0)  # Default to non-toxic on error
        
        return results
    
    def _make_request(self, text: str, test_mode: bool = False) -> Optional[Dict[str, Any]]:
        """
        Make request to Perspective API.
        
        Args:
            text: Text to analyze
            test_mode: If True, use minimal attributes for testing
            
        Returns:
            API response data or None if request fails
        """
        # Prepare request data
        request_data = {
            'comment': {'text': text},
            'requestedAttributes': {'TOXICITY': {}} if test_mode else self.attributes,
            'languages': ['en'],  # Support English by default
            'doNotStore': True  # Don't store data for privacy
        }
        
        try:
            response = requests.post(
                self.base_url,
                params={'key': self.api_key},
                json=request_data,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            # Update last request time for rate limiting
            self.last_request_time = time.time()
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logger.warning("Perspective API rate limit exceeded")
                time.sleep(2)  # Back off more aggressively
                return None
            else:
                logger.error(f"Perspective API error {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"Perspective API request timeout after {self.timeout}s")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Perspective API request failed: {e}")
            return None
    
    def _extract_score(self, response_data: Dict[str, Any], attribute: str) -> float:
        """
        Extract toxicity score from API response.
        
        Args:
            response_data: API response JSON
            attribute: Attribute to extract score for
            
        Returns:
            Toxicity score between 0.0 and 1.0
        """
        try:
            attributes = response_data.get('attributeScores', {})
            
            if attribute not in attributes:
                logger.warning(f"Attribute '{attribute}' not found in response")
                return 0.0
            
            summary_score = attributes[attribute].get('summaryScore', {})
            score = summary_score.get('value', 0.0)
            
            # Ensure score is in valid range
            return max(0.0, min(1.0, float(score)))
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to extract score from response: {e}")
            return 0.0
    
    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between API requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)
    
    def get_detailed_scores(self, text: str) -> Dict[str, float]:
        """
        Get detailed scores for all toxicity attributes.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary mapping attribute names to scores
        """
        self._validate_text(text)
        
        if not self.is_initialized:
            self.initialize()
        
        try:
            self._enforce_rate_limit()
            response_data = self._make_request(text)
            
            if not response_data:
                return {}
            
            scores = {}
            attributes = response_data.get('attributeScores', {})
            
            for attr_name in self.attributes:
                scores[attr_name] = self._extract_score(response_data, attr_name)
            
            return scores
            
        except Exception as e:
            self._record_error(e)
            logger.error(f"Failed to get detailed scores: {e}")
            return {}
    
    def cleanup(self) -> None:
        """Clean up resources (no persistent connections to close)."""
        self.is_initialized = False
        logger.debug("Perspective API engine cleaned up")
    
    @property
    def engine_type(self) -> str:
        """Return engine type identifier."""
        return "perspective_api"
    
    @property
    def supports_batch(self) -> bool:
        """Return False as Perspective API doesn't support true batch processing."""
        return False


# Register the Perspective API engine
if requests is not None:
    registry.register("perspective_api", PerspectiveAPIEngine)
    logger.info("Perspective API engine registered")
else:
    logger.warning("Requests library not available - Perspective API engine not registered")