"""
Tests for prompt generation module.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, mock_open

from reflectpause_core.prompts.generator import (
    PromptGenerator, PromptData, generate_prompt, 
    get_available_locales, reset_question_rotation
)


class TestPromptData:
    """Tests for PromptData dataclass."""
    
    def test_prompt_data_creation(self):
        """Test PromptData creation and attributes."""
        data = PromptData(
            title="Test Title",
            question="Test Question?",
            reflection_prompt="Think about it",
            continue_text="Continue",
            cancel_text="Cancel",
            locale="en"
        )
        
        assert data.title == "Test Title"
        assert data.question == "Test Question?"
        assert data.reflection_prompt == "Think about it"
        assert data.continue_text == "Continue"
        assert data.cancel_text == "Cancel"
        assert data.locale == "en"


class TestPromptGenerator:
    """Tests for PromptGenerator class."""
    
    def test_generator_initialization_with_no_locales_dir(self):
        """Test generator creates default locale when no directory exists."""
        with patch('pathlib.Path.exists', return_value=False):
            generator = PromptGenerator()
            
            assert "en" in generator._locales
            assert "cbt_questions" in generator._locales["en"]
            assert len(generator._locales["en"]["cbt_questions"]) > 0
    
    def test_generator_loads_locale_files(self):
        """Test generator loads locale files from directory."""
        locale_data = {
            "title": "Test Title",
            "cbt_questions": ["Question 1?", "Question 2?"],
            "reflection_prompt": "Reflect",
            "continue_text": "Continue",
            "cancel_text": "Cancel"
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock locale file
            locale_file = Path(temp_dir) / "test.json"
            with open(locale_file, 'w', encoding='utf-8') as f:
                json.dump(locale_data, f)
            
            # Mock the locales directory
            with patch('pathlib.Path.exists', return_value=True), \
                 patch('pathlib.Path.glob', return_value=[locale_file]), \
                 patch.object(Path, 'parent', new_callable=lambda: Path(temp_dir)):
                
                generator = PromptGenerator()
                
                assert "test" in generator._locales
                assert generator._locales["test"]["title"] == "Test Title"
    
    def test_generate_prompt_with_valid_locale(self):
        """Test prompt generation with valid locale."""
        generator = PromptGenerator()
        
        prompt = generator.generate_prompt("en")
        
        assert isinstance(prompt, PromptData)
        assert prompt.locale == "en"
        assert prompt.title
        assert prompt.question
        assert prompt.reflection_prompt
        assert prompt.continue_text
        assert prompt.cancel_text
    
    def test_generate_prompt_with_invalid_locale_falls_back_to_english(self):
        """Test prompt generation falls back to English for invalid locale."""
        generator = PromptGenerator()
        
        prompt = generator.generate_prompt("invalid")
        
        assert prompt.locale == "en"
    
    def test_generate_prompt_with_no_locales_raises_error(self):
        """Test prompt generation raises error when no locales available."""
        generator = PromptGenerator()
        generator._locales = {}
        
        with pytest.raises(ValueError, match="No locales available"):
            generator.generate_prompt("en")
    
    def test_question_rotation(self):
        """Test that questions rotate through the list."""
        generator = PromptGenerator()
        
        # Ensure we have multiple questions
        questions = generator._locales["en"]["cbt_questions"]
        assert len(questions) > 1
        
        # Generate multiple prompts and verify rotation
        first_prompt = generator.generate_prompt("en")
        second_prompt = generator.generate_prompt("en")
        
        assert first_prompt.question != second_prompt.question
    
    def test_question_rotation_wraps_around(self):
        """Test that question rotation wraps around to the beginning."""
        generator = PromptGenerator()
        
        questions = generator._locales["en"]["cbt_questions"]
        num_questions = len(questions)
        
        # Generate one more prompt than we have questions
        prompts = []
        for _ in range(num_questions + 1):
            prompt = generator.generate_prompt("en")
            prompts.append(prompt.question)
        
        # First and last should be the same (wrapped around)
        assert prompts[0] == prompts[-1]
    
    def test_get_available_locales(self):
        """Test getting available locales."""
        generator = PromptGenerator()
        
        locales = generator.get_available_locales()
        
        assert isinstance(locales, list)
        assert "en" in locales
    
    def test_reset_rotation_for_specific_locale(self):
        """Test resetting rotation for specific locale."""
        generator = PromptGenerator()
        
        # Advance rotation
        generator.generate_prompt("en")
        generator.generate_prompt("en")
        assert generator._question_indices["en"] > 0
        
        # Reset
        generator.reset_rotation("en")
        assert generator._question_indices["en"] == 0
    
    def test_reset_rotation_for_all_locales(self):
        """Test resetting rotation for all locales."""
        generator = PromptGenerator()
        
        # Advance rotation for multiple locales
        generator.generate_prompt("en")
        if "vi" in generator._locales:
            generator.generate_prompt("vi")
        
        # Reset all
        generator.reset_rotation()
        
        for locale in generator._question_indices:
            assert generator._question_indices[locale] == 0


class TestModuleFunctions:
    """Tests for module-level functions."""
    
    def test_generate_prompt_function(self):
        """Test module-level generate_prompt function."""
        prompt = generate_prompt("en")
        
        assert isinstance(prompt, PromptData)
        assert prompt.locale == "en"
    
    def test_get_available_locales_function(self):
        """Test module-level get_available_locales function."""
        locales = get_available_locales()
        
        assert isinstance(locales, list)
        assert "en" in locales
    
    def test_reset_question_rotation_function(self):
        """Test module-level reset_question_rotation function."""
        # This should not raise an error
        reset_question_rotation("en")
        reset_question_rotation()  # Reset all
    
    def test_prompt_generation_consistency(self):
        """Test that prompt generation is consistent across calls."""
        prompt1 = generate_prompt("en")
        prompt2 = generate_prompt("en")
        
        # Should have same structure but potentially different questions
        assert prompt1.locale == prompt2.locale
        assert prompt1.title == prompt2.title
        assert prompt1.reflection_prompt == prompt2.reflection_prompt
        assert prompt1.continue_text == prompt2.continue_text
        assert prompt1.cancel_text == prompt2.cancel_text