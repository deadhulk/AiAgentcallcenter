import pytest
from src.agent.tts_engine import TTSEngine
from unittest.mock import patch, MagicMock
import os

@pytest.fixture
def tts_engine():
    return TTSEngine()

def test_text_to_speech_generation(tts_engine):
    test_text = "Hello, this is a test message"
    
    with patch('src.agent.tts_engine.gTTS') as mock_gtts:
        # Mock the gTTS instance
        mock_tts_instance = MagicMock()
        mock_gtts.return_value = mock_tts_instance
        
        # Call the text_to_speech method
        audio_path = tts_engine.text_to_speech(test_text)
        
        # Verify gTTS was called with correct parameters
        mock_gtts.assert_called_once_with(text=test_text, lang='en', slow=False)
        
        # Verify save was called
        assert mock_tts_instance.save.called
        
        # Verify the file path was returned
        assert audio_path.endswith('.mp3')
        
        # Clean up the generated file
        tts_engine.cleanup_audio_file(audio_path)

def test_cleanup_audio_file(tts_engine):
    # Create a temporary file
    with open('test_audio.mp3', 'w') as f:
        f.write('test')
    
    # Test cleanup
    tts_engine.cleanup_audio_file('test_audio.mp3')
    
    # Verify file was deleted
    assert not os.path.exists('test_audio.mp3')

def test_cleanup_nonexistent_file(tts_engine):
    # Should not raise an error when file doesn't exist
    tts_engine.cleanup_audio_file('nonexistent_file.mp3')