from typing import Any
from .adapters import get_tts_adapter


class TTSEngine:
    """Wrapper that delegates to a pluggable TTS adapter chosen by env var."""
    def __init__(self):
        self.adapter = get_tts_adapter()

    def text_to_speech(self, text: str) -> str:
        return self.adapter.synthesize(text)

    def cleanup_audio_file(self, file_path: str):
        import os
        if os.path.exists(file_path):
            os.remove(file_path)