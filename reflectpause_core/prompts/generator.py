"""
CBT prompt generation with question rotation and localization.
"""

import json
import random
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Set
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PromptData:
    """Container for localized prompt data."""
    
    title: str
    question: str
    reflection_prompt: str
    continue_text: str
    cancel_text: str
    locale: str


class PromptGenerator:
    """Manages CBT question rotation and localization with intelligent language detection."""
    
    # Language family mappings for fallback
    LANGUAGE_FAMILIES = {
        'en': ['en-US', 'en-GB', 'en-CA', 'en-AU'],
        'es': ['es-ES', 'es-MX', 'es-AR', 'es-CL', 'es-CO', 'es-PE', 'es-VE'],
        'fr': ['fr-FR', 'fr-CA', 'fr-BE', 'fr-CH'],
        'de': ['de-DE', 'de-AT', 'de-CH'],
        'pt': ['pt-BR', 'pt-PT'],
        'zh': ['zh-CN', 'zh-TW', 'zh-HK', 'zh-SG'],
        'ar': ['ar-SA', 'ar-EG', 'ar-AE', 'ar-MA', 'ar-DZ', 'ar-TN'],
    }
    
    # Common locale alias mappings
    LOCALE_ALIASES = {
        'chinese': 'zh',
        'mandarin': 'zh',
        'japanese': 'ja',
        'korean': 'ko',
        'arabic': 'ar',
        'hindi': 'hi',
        'spanish': 'es',
        'french': 'fr',
        'german': 'de',
        'portuguese': 'pt',
        'italian': 'it',
        'dutch': 'nl',
        'russian': 'ru',
        'vietnamese': 'vi',
        'english': 'en',
    }
    
    def __init__(self):
        self._locales: Dict[str, Dict[str, Any]] = {}
        self._question_indices: Dict[str, int] = {}
        self._supported_locales: Set[str] = set()
        self._load_locales()
    
    def _load_locales(self) -> None:
        """Load all available locale files."""
        locales_dir = Path(__file__).parent / "locales"
        
        if not locales_dir.exists():
            logger.warning(f"Locales directory not found: {locales_dir}")
            self._create_default_locales()
            return
        
        for locale_file in locales_dir.glob("*.json"):
            locale_code = locale_file.stem
            try:
                with open(locale_file, 'r', encoding='utf-8') as f:
                    self._locales[locale_code] = json.load(f)
                    self._question_indices[locale_code] = 0
                    self._supported_locales.add(locale_code)
                logger.info(f"Loaded locale: {locale_code}")
            except Exception as e:
                logger.error(f"Failed to load locale {locale_code}: {e}")
        
        if not self._locales:
            self._create_default_locales()
        
        logger.info(f"Supported locales: {sorted(self._supported_locales)}")
    
    def _create_default_locales(self) -> None:
        """Create default English locale data."""
        default_en = {
            "title": "Take a moment to reflect",
            "cbt_questions": [
                "What specific event or situation triggered this feeling?",
                "What thoughts are going through your mind right now?",
                "How would you rate the intensity of this emotion from 1-10?",
                "What evidence supports this thought? What evidence challenges it?",
                "How might a good friend respond to this situation?",
                "What would you tell a friend who was experiencing this?",
                "What's the worst that could realistically happen? What's the best?",
                "How important will this be in 5 years?",
                "What actions could you take to improve this situation?",
                "What have you learned from similar situations in the past?"
            ],
            "reflection_prompt": "Take a moment to consider your response before sending:",
            "continue_text": "Send anyway",
            "cancel_text": "Edit message"
        }
        
        self._locales["en"] = default_en
        self._question_indices["en"] = 0
        self._supported_locales.add("en")
        logger.info("Created default English locale")
    
    def normalize_locale(self, locale: str) -> str:
        """
        Normalize and resolve locale to supported format.
        
        Args:
            locale: Input locale string
            
        Returns:
            Normalized locale code
        """
        if not locale:
            return "en"
        
        # Convert to lowercase for consistency
        locale = locale.lower().strip()
        
        # Check direct match first
        if locale in self._supported_locales:
            return locale
        
        # Check aliases
        if locale in self.LOCALE_ALIASES:
            alias_locale = self.LOCALE_ALIASES[locale]
            if alias_locale in self._supported_locales:
                return alias_locale
        
        # Check language family mappings (e.g., en-US -> en)
        for base_lang, variants in self.LANGUAGE_FAMILIES.items():
            if locale in variants and base_lang in self._supported_locales:
                return base_lang
        
        # Extract base language from complex locale (e.g., zh-CN -> zh)
        if '-' in locale:
            base_lang = locale.split('-')[0]
            if base_lang in self._supported_locales:
                return base_lang
        
        # Extract language from underscore format (e.g., en_US -> en)
        if '_' in locale:
            base_lang = locale.split('_')[0]
            if base_lang in self._supported_locales:
                return base_lang
        
        # Fallback to English
        logger.warning(f"Locale '{locale}' not supported, falling back to English")
        return "en"
    
    def detect_language_from_text(self, text: str) -> str:
        """
        Simple language detection based on character patterns.
        
        Args:
            text: Text to analyze
            
        Returns:
            Detected locale code
        """
        if not text:
            return "en"
        
        # Count characters for each script to handle mixed content better
        char_counts = {
            'zh': len(re.findall(r'[\u4e00-\u9fff]', text)),  # Chinese characters
            'ja': len(re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', text)),  # Japanese hiragana/katakana
            'ko': len(re.findall(r'[\uac00-\ud7af]', text)),  # Korean characters
            'ar': len(re.findall(r'[\u0600-\u06ff]', text)),  # Arabic characters
            'hi': len(re.findall(r'[\u0900-\u097f]', text)),  # Hindi/Devanagari
            'ru': len(re.findall(r'[\u0400-\u04ff]', text)),  # Cyrillic (Russian)
        }
        
        # Find the script with the most characters
        max_count = max(char_counts.values())
        if max_count > 0:
            for script, count in char_counts.items():
                if count == max_count and script in self._supported_locales:
                    return script
        
        # Handle Japanese vs Chinese ambiguity (Chinese chars can appear in Japanese)
        if char_counts['ja'] > 0 and char_counts['zh'] > 0:
            # If we have hiragana/katakana, it's probably Japanese
            if char_counts['ja'] > 0:
                return "ja"
        
        # If no specific script detected, return English
        return "en"
    
    def generate_prompt(self, locale: str = "en") -> PromptData:
        """
        Generate a localized prompt with rotated CBT question.
        
        Args:
            locale: Language locale code (supports various formats and aliases)
            
        Returns:
            PromptData with localized strings and rotated question
            
        Raises:
            ValueError: If no locales are available
        """
        # Normalize the locale
        resolved_locale = self.normalize_locale(locale)
        
        if resolved_locale not in self._locales:
            if "en" not in self._locales:
                raise ValueError("No locales available")
            resolved_locale = "en"
        
        locale_data = self._locales[resolved_locale]
        questions = locale_data.get("cbt_questions", [])
        
        if not questions:
            raise ValueError(f"No CBT questions found for locale '{resolved_locale}'")
        
        # Rotate to next question
        current_index = self._question_indices[resolved_locale]
        question = questions[current_index]
        
        # Update index for next call
        self._question_indices[resolved_locale] = (current_index + 1) % len(questions)
        
        return PromptData(
            title=locale_data.get("title", "Take a moment to reflect"),
            question=question,
            reflection_prompt=locale_data.get("reflection_prompt", "Take a moment to consider:"),
            continue_text=locale_data.get("continue_text", "Continue"),
            cancel_text=locale_data.get("cancel_text", "Cancel"),
            locale=resolved_locale
        )
    
    def get_available_locales(self) -> List[str]:
        """Get list of available locale codes."""
        return sorted(list(self._supported_locales))
    
    def get_locale_info(self, locale: str) -> Dict[str, Any]:
        """
        Get information about a specific locale.
        
        Args:
            locale: Locale code
            
        Returns:
            Dictionary with locale information
        """
        # Check if the original locale is directly supported
        if locale in self._supported_locales:
            locale_data = self._locales[locale]
            return {
                'locale': locale,
                'resolved_locale': locale,
                'available': True,
                'title': locale_data.get('title', ''),
                'question_count': len(locale_data.get('cbt_questions', [])),
                'current_question_index': self._question_indices.get(locale, 0)
            }
        
        # Try to resolve through normalization
        resolved_locale = self.normalize_locale(locale)
        
        # If normalization resulted in fallback to English due to unsupported locale
        if resolved_locale == "en" and locale.lower() not in ["en", "english"] and not any(
            locale.lower().startswith(variant.lower()) for variant in self.LANGUAGE_FAMILIES.get("en", [])
        ):
            # This means it's truly unsupported
            return {
                'locale': locale,
                'resolved_locale': resolved_locale,
                'available': False,
                'fallback': 'en'
            }
        
        # It's supported through normalization
        locale_data = self._locales[resolved_locale]
        return {
            'locale': locale,
            'resolved_locale': resolved_locale,
            'available': True,
            'title': locale_data.get('title', ''),
            'question_count': len(locale_data.get('cbt_questions', [])),
            'current_question_index': self._question_indices.get(resolved_locale, 0)
        }
    
    def supports_locale(self, locale: str) -> bool:
        """
        Check if a locale is supported (directly or through fallback).
        
        Args:
            locale: Locale code to check
            
        Returns:
            True if locale is supported
        """
        # Direct support
        if locale in self._supported_locales:
            return True
        
        # Check if it can be normalized to a supported locale
        resolved_locale = self.normalize_locale(locale)
        
        # If it resolved to English but wasn't an English variant, it's unsupported
        if resolved_locale == "en" and locale.lower() not in ["en", "english"] and not any(
            locale.lower().startswith(variant.lower()) for variant in self.LANGUAGE_FAMILIES.get("en", [])
        ) and locale.lower() not in self.LOCALE_ALIASES:
            return False
        
        return resolved_locale in self._locales
    
    def get_language_families(self) -> Dict[str, List[str]]:
        """Get supported language families and their variants."""
        supported_families = {}
        for base_lang, variants in self.LANGUAGE_FAMILIES.items():
            if base_lang in self._supported_locales:
                supported_families[base_lang] = variants
        return supported_families
    
    def reset_rotation(self, locale: str = None) -> None:
        """Reset question rotation for specified locale or all locales."""
        if locale:
            resolved_locale = self.normalize_locale(locale)
            if resolved_locale in self._question_indices:
                self._question_indices[resolved_locale] = 0
        else:
            for loc in self._question_indices:
                self._question_indices[loc] = 0


# Global generator instance
_generator = PromptGenerator()


def generate_prompt(locale: str = "en") -> PromptData:
    """
    Generate a localized CBT prompt with question rotation.
    
    Args:
        locale: Language locale (e.g., 'en', 'vi')
        
    Returns:
        PromptData object with localized prompt strings
    """
    return _generator.generate_prompt(locale)


def get_available_locales() -> List[str]:
    """Get list of available language locales."""
    return _generator.get_available_locales()


def reset_question_rotation(locale: str = None) -> None:
    """Reset CBT question rotation for locale or all locales."""
    _generator.reset_rotation(locale)


def normalize_locale(locale: str) -> str:
    """
    Normalize locale string to supported format.
    
    Args:
        locale: Input locale string
        
    Returns:
        Normalized locale code
    """
    return _generator.normalize_locale(locale)


def detect_language_from_text(text: str) -> str:
    """
    Detect language from text using character pattern analysis.
    
    Args:
        text: Text to analyze
        
    Returns:
        Detected locale code
    """
    return _generator.detect_language_from_text(text)


def get_locale_info(locale: str) -> Dict[str, Any]:
    """
    Get detailed information about a locale.
    
    Args:
        locale: Locale code to check
        
    Returns:
        Dictionary with locale information
    """
    return _generator.get_locale_info(locale)


def supports_locale(locale: str) -> bool:
    """
    Check if a locale is supported.
    
    Args:
        locale: Locale code to check
        
    Returns:
        True if locale is supported
    """
    return _generator.supports_locale(locale)


def get_language_families() -> Dict[str, List[str]]:
    """
    Get supported language families and their variants.
    
    Returns:
        Dictionary mapping base languages to variant codes
    """
    return _generator.get_language_families()


def generate_prompt_auto_detect(text: str, preferred_locale: str = None) -> PromptData:
    """
    Generate prompt with automatic language detection.
    
    Args:
        text: Text to analyze for language detection
        preferred_locale: Preferred locale if detection fails
        
    Returns:
        PromptData in detected or preferred language
    """
    # Try to detect language from text
    detected_locale = detect_language_from_text(text)
    
    # Use preferred locale if provided and supported (and it's truly supported, not just fallback)
    if preferred_locale and _generator.supports_locale(preferred_locale):
        target_locale = preferred_locale
    else:
        target_locale = detected_locale
    
    return generate_prompt(target_locale)