from typing import Optional, Any
from .adapters import get_stt_adapter


class SpeechRecognitionEngine:
    """Wrapper that delegates to a pluggable STT adapter chosen by env var.

    Use STT_PROVIDER to select an implementation; defaults to 'mock' which
    uses the local speech_recognition library.
    """
    def __init__(self):
        self.adapter = get_stt_adapter()

    def recognize_from_audio(self, audio_data: Any) -> Optional[str]:
        return self.adapter.recognize(audio_data)