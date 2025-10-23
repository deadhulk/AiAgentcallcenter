import pytest
import os
from src.agent.speech_recognition import SpeechRecognitionEngine
from src.agent.tts_engine import TTSEngine

@pytest.fixture
def speech_recognition_engine():
    return SpeechRecognitionEngine()

@pytest.fixture
def tts_engine():
    return TTSEngine()

def test_sample_transcript_exists():
    assert os.path.exists('tests/sample_audio/sample_transcript.txt')

def test_dummy_audio_exists():
    assert os.path.exists('tests/sample_audio/dummy_audio.txt')

def test_tts_with_sample_text(tts_engine):
    audio_path = tts_engine.text_to_speech("Hello, this is a test message")
    assert audio_path.endswith('.mp3')
    tts_engine.cleanup_audio_file(audio_path)

def test_speech_recognition_with_dummy_file(speech_recognition_engine):
    # This is a placeholder: in real tests, use a real audio file
    # Here, just check that the engine can be called
    assert speech_recognition_engine is not None
