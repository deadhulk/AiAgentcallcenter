import pytest
from src.agent.speech_recognition import SpeechRecognitionEngine
import speech_recognition as sr
from unittest.mock import Mock, patch

@pytest.fixture
def speech_recognition_engine():
    return SpeechRecognitionEngine()

@pytest.fixture
def mock_audio_data():
    # Create a mock AudioData object
    mock_audio = Mock(spec=sr.AudioData)
    return mock_audio

def test_speech_recognition_success(speech_recognition_engine, mock_audio_data):
    with patch('speech_recognition.Recognizer.recognize_google') as mock_recognize:
        mock_recognize.return_value = "Hello, this is a test"
        
        result = speech_recognition_engine.recognize_from_audio(mock_audio_data)
        
        assert result == "Hello, this is a test"
        mock_recognize.assert_called_once_with(mock_audio_data)

def test_speech_recognition_unknown_value(speech_recognition_engine, mock_audio_data):
    with patch('speech_recognition.Recognizer.recognize_google') as mock_recognize:
        mock_recognize.side_effect = sr.UnknownValueError()
        
        result = speech_recognition_engine.recognize_from_audio(mock_audio_data)
        
        assert result is None

def test_speech_recognition_request_error(speech_recognition_engine, mock_audio_data):
    with patch('speech_recognition.Recognizer.recognize_google') as mock_recognize:
        mock_recognize.side_effect = sr.RequestError("API unavailable")
        
        result = speech_recognition_engine.recognize_from_audio(mock_audio_data)
        
        assert result is None