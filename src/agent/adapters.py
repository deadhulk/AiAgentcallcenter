from typing import Any, Optional
import os
import logging

logger = logging.getLogger(__name__)


class BaseSTTAdapter:
    """Base class for Speech-To-Text adapters."""
    def recognize(self, audio_data: Any) -> Optional[str]:
        raise NotImplementedError()


class MockSTTAdapter(BaseSTTAdapter):
    """Fallback adapter that uses the existing speech_recognition library.

    Keeps behavior compatible with the current PoC while allowing replacement
    with industrial providers (Google, Amazon, Azure) later.
    """
    def __init__(self):
        try:
            import speech_recognition as sr
        except Exception:
            sr = None
        self.sr = sr
        if sr is None:
            logger.warning("speech_recognition not available; MockSTTAdapter will always return None")

    def recognize(self, audio_data: Any) -> Optional[str]:
        if self.sr is None:
            return None
        try:
            return self.sr.Recognizer().recognize_google(audio_data)
        except Exception:
            return None


class BaseTTSAdapter:
    """Base class for Text-To-Speech adapters."""
    def synthesize(self, text: str) -> str:
        """Synthesize text and return path to audio file."""
        raise NotImplementedError()


class GTTSAdapter(BaseTTSAdapter):
    """Adapter that uses gTTS as a simple TTS provider (PoC-level).

    This remains the default for local/demo deployments. For production, add
    Polly/Google/ElevenLabs adapters that return high-quality audio.
    """
    def __init__(self, language: str = "en"):
        try:
            from gtts import gTTS
        except Exception:
            gTTS = None
        self.gTTS = gTTS
        self.language = language

    def synthesize(self, text: str) -> str:
        if self.gTTS is None:
            raise RuntimeError("gTTS not available")
        import tempfile, os
        tts = self.gTTS(text=text, lang=self.language, slow=False)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        path = temp_file.name
        temp_file.close()
        tts.save(path)
        return path


def get_stt_adapter() -> BaseSTTAdapter:
    """Factory to select STT adapter via environment variable STT_PROVIDER.

    Supported values (case-insensitive):
    - 'mock' (default): Local speech_recognition library
    - 'whisper': OpenAI Whisper API
    - 'aws': Amazon Transcribe
    """
    provider = os.getenv("STT_PROVIDER", "mock").lower()
    
    if provider == "mock":
        return MockSTTAdapter()
    elif provider == "whisper":
        from .openai_adapters import OpenAIWhisperAdapter
        return OpenAIWhisperAdapter()
    elif provider == "aws":
        from .aws_adapters import AWSTranscribeAdapter
        return AWSTranscribeAdapter()
    
    logger.warning("STT provider %s not implemented, falling back to mock", provider)
    return MockSTTAdapter()


def get_tts_adapter() -> BaseTTSAdapter:
    """Factory to select TTS adapter via environment variable TTS_PROVIDER.
    
    Supported values (case-insensitive):
    - 'gtts' (default): Google Text-to-Speech
    - 'openai': OpenAI TTS API
    - 'polly': Amazon Polly
    """
    provider = os.getenv("TTS_PROVIDER", "gtts").lower()
    
    if provider == "gtts":
        return GTTSAdapter(language=os.getenv("TTS_LANGUAGE", "en"))
    elif provider == "openai":
        from .openai_adapters import OpenAITTSAdapter
        return OpenAITTSAdapter(voice=os.getenv("OPENAI_TTS_VOICE", "alloy"))
    elif provider == "polly":
        from .aws_adapters import AWSPollyAdapter
        return AWSPollyAdapter(voice_id=os.getenv("AWS_POLLY_VOICE", "Joanna"))
    
    logger.warning("TTS provider %s not implemented, falling back to gTTS", provider)
    return GTTSAdapter(language=os.getenv("TTS_LANGUAGE", "en"))


def get_llm_adapter():
    """Factory to select LLM adapter via environment variable LLM_PROVIDER.
    
    Supported values (case-insensitive):
    - 'openai' (default): OpenAI GPT models
    """
    from .openai_adapters import get_llm_adapter as get_openai_llm
    return get_openai_llm()
