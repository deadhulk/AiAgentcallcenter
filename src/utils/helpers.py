import io
import wave
from typing import Any

def convert_audio_to_wav(audio_data: bytes) -> Any:
    """
    Convert audio data to WAV format
    """
    # Create an in-memory wave file
    wav_file = io.BytesIO()
    with wave.open(wav_file, 'wb') as wave_writer:
        wave_writer.setnchannels(1)  # Mono
        wave_writer.setsampwidth(2)  # 2 bytes per sample
        wave_writer.setframerate(16000)  # 16kHz sampling rate
        wave_writer.writeframes(audio_data)
    
    return wav_file.getvalue()

def validate_audio_format(audio_data: bytes) -> bool:
    """
    Validate that the audio data is in a supported format
    """
    try:
        with wave.open(io.BytesIO(audio_data), 'rb') as wave_reader:
            return True
    except:
        return False