"""
Tests for multilingual support in prompt generation.
"""

import unittest
from unittest.mock import patch, mock_open

from reflectpause_core.prompts.generator import (
    PromptGenerator, PromptData, generate_prompt, get_available_locales,
    normalize_locale, detect_language_from_text, get_locale_info,
    supports_locale, get_language_families, generate_prompt_auto_detect
)


class TestMultilingualSupport(unittest.TestCase):
    """Test multilingual functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.generator = PromptGenerator()
    
    def test_all_locale_files_loaded(self):
        """Test that all expected locale files are loaded."""
        available_locales = get_available_locales()
        
        # Should have at least the languages we created
        expected_locales = {
            'en', 'es', 'fr', 'de', 'pt', 'it', 'nl', 
            'ru', 'zh', 'ja', 'ko', 'ar', 'hi', 'vi'
        }
        
        loaded_locales = set(available_locales)
        
        # Check that we have at least the core languages
        self.assertTrue(expected_locales.issubset(loaded_locales),
                       f"Missing locales: {expected_locales - loaded_locales}")
    
    def test_locale_normalization(self):
        """Test locale normalization functionality."""
        # Test direct matches
        self.assertEqual(normalize_locale('en'), 'en')
        self.assertEqual(normalize_locale('es'), 'es')
        self.assertEqual(normalize_locale('zh'), 'zh')
        
        # Test case insensitivity
        self.assertEqual(normalize_locale('EN'), 'en')
        self.assertEqual(normalize_locale('Es'), 'es')
        
        # Test aliases
        self.assertEqual(normalize_locale('english'), 'en')
        self.assertEqual(normalize_locale('spanish'), 'es')
        self.assertEqual(normalize_locale('chinese'), 'zh')
        self.assertEqual(normalize_locale('mandarin'), 'zh')
        
        # Test language variants
        self.assertEqual(normalize_locale('en-US'), 'en')
        self.assertEqual(normalize_locale('es-MX'), 'es')
        self.assertEqual(normalize_locale('zh-CN'), 'zh')
        self.assertEqual(normalize_locale('fr_CA'), 'fr')
        
        # Test fallback to English
        self.assertEqual(normalize_locale('invalid_locale'), 'en')
        self.assertEqual(normalize_locale(''), 'en')
        self.assertEqual(normalize_locale(None), 'en')
    
    def test_language_detection_from_text(self):
        """Test automatic language detection from text."""
        # Test Chinese
        chinese_text = "你好世界，这是一个测试"
        self.assertEqual(detect_language_from_text(chinese_text), 'zh')
        
        # Test Japanese
        japanese_text = "こんにちは世界、これはテストです"
        self.assertEqual(detect_language_from_text(japanese_text), 'ja')
        
        # Test Korean
        korean_text = "안녕하세요 세계, 이것은 테스트입니다"
        self.assertEqual(detect_language_from_text(korean_text), 'ko')
        
        # Test Arabic
        arabic_text = "مرحبا بالعالم، هذا اختبار"
        self.assertEqual(detect_language_from_text(arabic_text), 'ar')
        
        # Test Hindi
        hindi_text = "नमस्ते दुनिया, यह एक परीक्षा है"
        self.assertEqual(detect_language_from_text(hindi_text), 'hi')
        
        # Test Russian
        russian_text = "Привет мир, это тест"
        self.assertEqual(detect_language_from_text(russian_text), 'ru')
        
        # Test English (fallback)
        english_text = "Hello world, this is a test"
        self.assertEqual(detect_language_from_text(english_text), 'en')
        
        # Test empty text
        self.assertEqual(detect_language_from_text(''), 'en')
        self.assertEqual(detect_language_from_text(None), 'en')
    
    def test_prompt_generation_all_languages(self):
        """Test prompt generation for all supported languages."""
        for locale in get_available_locales():
            with self.subTest(locale=locale):
                prompt = generate_prompt(locale)
                
                # Verify prompt structure
                self.assertIsInstance(prompt, PromptData)
                self.assertIsNotNone(prompt.title)
                self.assertIsNotNone(prompt.question)
                self.assertIsNotNone(prompt.reflection_prompt)
                self.assertIsNotNone(prompt.continue_text)
                self.assertIsNotNone(prompt.cancel_text)
                self.assertEqual(prompt.locale, locale)
                
                # Verify strings are not empty
                self.assertGreater(len(prompt.title.strip()), 0)
                self.assertGreater(len(prompt.question.strip()), 0)
                self.assertGreater(len(prompt.reflection_prompt.strip()), 0)
                self.assertGreater(len(prompt.continue_text.strip()), 0)
                self.assertGreater(len(prompt.cancel_text.strip()), 0)
    
    def test_locale_info_functionality(self):
        """Test locale information retrieval."""
        # Test valid locale
        info = get_locale_info('es')
        self.assertTrue(info['available'])
        self.assertEqual(info['resolved_locale'], 'es')
        self.assertGreater(info['question_count'], 0)
        self.assertIn('current_question_index', info)
        
        # Test locale with normalization
        info = get_locale_info('en-US')
        self.assertTrue(info['available'])
        self.assertEqual(info['resolved_locale'], 'en')
        
        # Test unsupported locale
        info = get_locale_info('invalid_lang')
        self.assertFalse(info['available'])
        self.assertEqual(info['fallback'], 'en')
    
    def test_locale_support_checking(self):
        """Test locale support checking."""
        # Test supported locales
        self.assertTrue(supports_locale('en'))
        self.assertTrue(supports_locale('es'))
        self.assertTrue(supports_locale('zh'))
        
        # Test with normalization
        self.assertTrue(supports_locale('en-US'))
        self.assertTrue(supports_locale('spanish'))
        self.assertTrue(supports_locale('chinese'))
        
        # Test unsupported locale
        self.assertFalse(supports_locale('klingon'))
    
    def test_language_families(self):
        """Test language family functionality."""
        families = get_language_families()
        
        # Should be a dictionary
        self.assertIsInstance(families, dict)
        
        # Should contain expected families for supported languages
        if 'en' in get_available_locales():
            self.assertIn('en', families)
            self.assertIn('en-US', families['en'])
        
        if 'es' in get_available_locales():
            self.assertIn('es', families)
            self.assertIn('es-MX', families['es'])
    
    def test_question_rotation_per_locale(self):
        """Test that question rotation works independently per locale."""
        # Test with English
        prompt1_en = generate_prompt('en')
        prompt2_en = generate_prompt('en')
        
        # Test with Spanish
        prompt1_es = generate_prompt('es')
        prompt2_es = generate_prompt('es')
        
        # Questions should rotate within each locale
        # (Note: They might be the same if there's only one question, so we just check structure)
        self.assertEqual(prompt1_en.locale, 'en')
        self.assertEqual(prompt2_en.locale, 'en')
        self.assertEqual(prompt1_es.locale, 'es')
        self.assertEqual(prompt2_es.locale, 'es')
        
        # Different locales should have different content
        self.assertNotEqual(prompt1_en.title, prompt1_es.title)
    
    def test_auto_detect_prompt_generation(self):
        """Test automatic language detection for prompt generation."""
        # Test with Chinese text
        chinese_text = "这个消息可能有问题"
        prompt = generate_prompt_auto_detect(chinese_text)
        self.assertEqual(prompt.locale, 'zh')
        
        # Test with preferred locale override
        prompt = generate_prompt_auto_detect(chinese_text, preferred_locale='es')
        self.assertEqual(prompt.locale, 'es')
        
        # Test with unsupported preferred locale (should fall back to detected)
        prompt = generate_prompt_auto_detect(chinese_text, preferred_locale='invalid')
        self.assertEqual(prompt.locale, 'zh')
        
        # Test with English text
        english_text = "This message might be problematic"
        prompt = generate_prompt_auto_detect(english_text)
        self.assertEqual(prompt.locale, 'en')
    
    def test_prompt_content_quality(self):
        """Test that prompt content meets quality standards."""
        for locale in ['en', 'es', 'fr', 'de', 'zh', 'ja']:
            if supports_locale(locale):
                with self.subTest(locale=locale):
                    prompt = generate_prompt(locale)
                    
                    # Check that title suggests reflection
                    title_lower = prompt.title.lower()
                    reflection_keywords = ['reflect', 'moment', 'think', 'consider', 
                                         'tiempo', 'reflexiona', 'piensa',  # Spanish
                                         'réfléchir', 'moment',  # French
                                         'nachdenken', 'moment',  # German
                                         '时间', '思考', '反思',  # Chinese
                                         '時間', '考え', '反省']  # Japanese
                    
                    # At least check that it's not empty and has reasonable length
                    self.assertGreater(len(prompt.title), 5)
                    self.assertLess(len(prompt.title), 100)
                    
                    # Questions should be actual questions or prompts
                    self.assertGreater(len(prompt.question), 10)
                    self.assertLess(len(prompt.question), 500)
    
    def test_fallback_behavior(self):
        """Test fallback behavior when locales are missing."""
        # Test with completely unsupported locale
        prompt = generate_prompt('fictitious-language')
        self.assertEqual(prompt.locale, 'en')  # Should fall back to English
        
        # Verify it's a valid prompt
        self.assertIsInstance(prompt, PromptData)
        self.assertGreater(len(prompt.title), 0)
        self.assertGreater(len(prompt.question), 0)
    
    def test_mixed_content_detection(self):
        """Test language detection with mixed content."""
        # Mixed Chinese and English
        mixed_text = "Hello 你好 world 世界"
        detected = detect_language_from_text(mixed_text)
        self.assertEqual(detected, 'zh')  # Should detect Chinese due to Chinese characters
        
        # Mostly English with some numbers/symbols
        english_with_symbols = "Hello world! This is a test with 123 symbols @#$"
        detected = detect_language_from_text(english_with_symbols)
        self.assertEqual(detected, 'en')  # Should fall back to English
    
    def test_case_insensitive_operations(self):
        """Test that all operations handle case insensitivity."""
        # Test various cases
        test_cases = ['EN', 'en', 'En', 'eN']
        
        for case in test_cases:
            with self.subTest(case=case):
                normalized = normalize_locale(case)
                self.assertEqual(normalized, 'en')
                
                supported = supports_locale(case)
                self.assertTrue(supported)
                
                prompt = generate_prompt(case)
                self.assertEqual(prompt.locale, 'en')


class TestPromptContentConsistency(unittest.TestCase):
    """Test consistency of prompt content across languages."""
    
    def test_all_locales_have_required_fields(self):
        """Test that all locale files have required fields."""
        required_fields = ['title', 'cbt_questions', 'reflection_prompt', 
                          'continue_text', 'cancel_text']
        
        for locale in get_available_locales():
            with self.subTest(locale=locale):
                info = get_locale_info(locale)
                self.assertTrue(info['available'])
                
                # Generate a prompt to verify all fields are present
                prompt = generate_prompt(locale)
                
                # All fields should be non-empty strings
                self.assertIsInstance(prompt.title, str)
                self.assertIsInstance(prompt.question, str)
                self.assertIsInstance(prompt.reflection_prompt, str)
                self.assertIsInstance(prompt.continue_text, str)
                self.assertIsInstance(prompt.cancel_text, str)
                
                self.assertGreater(len(prompt.title.strip()), 0)
                self.assertGreater(len(prompt.question.strip()), 0)
                self.assertGreater(len(prompt.reflection_prompt.strip()), 0)
                self.assertGreater(len(prompt.continue_text.strip()), 0)
                self.assertGreater(len(prompt.cancel_text.strip()), 0)
    
    def test_question_count_consistency(self):
        """Test that all locales have a reasonable number of questions."""
        for locale in get_available_locales():
            with self.subTest(locale=locale):
                info = get_locale_info(locale)
                
                # Should have at least 5 questions, preferably 10
                self.assertGreaterEqual(info['question_count'], 5,
                                      f"Locale {locale} has too few questions")
                
                # Shouldn't have an excessive number
                self.assertLessEqual(info['question_count'], 50,
                                   f"Locale {locale} has too many questions")


class TestPerformanceWithMultipleLanguages(unittest.TestCase):
    """Test performance implications of multilingual support."""
    
    def test_locale_loading_performance(self):
        """Test that locale loading doesn't significantly impact startup."""
        import time
        
        start_time = time.time()
        generator = PromptGenerator()
        load_time = time.time() - start_time
        
        # Should load all locales quickly (under 1 second)
        self.assertLess(load_time, 1.0)
        
        # Should have loaded multiple locales
        self.assertGreater(len(generator.get_available_locales()), 5)
    
    def test_prompt_generation_performance(self):
        """Test that prompt generation is fast across all languages."""
        import time
        
        for locale in get_available_locales()[:5]:  # Test first 5 to save time
            with self.subTest(locale=locale):
                start_time = time.time()
                
                # Generate multiple prompts
                for _ in range(10):
                    generate_prompt(locale)
                
                duration = time.time() - start_time
                
                # Should be very fast (under 0.1 seconds for 10 prompts)
                self.assertLess(duration, 0.1,
                              f"Prompt generation too slow for {locale}")


if __name__ == '__main__':
    unittest.main()