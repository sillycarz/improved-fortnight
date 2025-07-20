"""
CBT prompt generation and localization with comprehensive multilingual support.
"""

from .generator import (
    generate_prompt, get_available_locales, reset_question_rotation, PromptData,
    normalize_locale, detect_language_from_text, get_locale_info, supports_locale,
    get_language_families, generate_prompt_auto_detect
)

__all__ = [
    "generate_prompt", "get_available_locales", "reset_question_rotation", "PromptData",
    "normalize_locale", "detect_language_from_text", "get_locale_info", "supports_locale", 
    "get_language_families", "generate_prompt_auto_detect"
]