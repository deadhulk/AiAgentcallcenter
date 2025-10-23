import pytest
from src.utils.helpers import convert_audio_to_wav, validate_audio_format
import io
import wave

def test_convert_audio_to_wav():
    # Create sample audio data
    sample_rate = 16000
    sample_width = 2
    channels = 1
    
    # Create sample PCM data
    pcm_data = b'\x00\x00' * sample_rate  # 1 second of silence
    
    # Convert to WAV
    wav_data = convert_audio_to_wav(pcm_data)
    
    # Verify the WAV format
    with wave.open(io.BytesIO(wav_data), 'rb') as wav_file:
        assert wav_file.getnchannels() == channels
        assert wav_file.getsampwidth() == sample_width
        assert wav_file.getframerate() == sample_rate

def test_validate_audio_format_valid():
    # Create a valid WAV file
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b'\x00\x00' * 16000)
    
    valid_wav_data = buffer.getvalue()
    assert validate_audio_format(valid_wav_data) == True

def test_validate_audio_format_invalid():
    # Test with invalid data
    invalid_data = b'not a wav file'
    assert validate_audio_format(invalid_data) == False