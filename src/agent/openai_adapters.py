"""OpenAI adapters for STT, TTS, and LLM services."""
from typing import Any, Dict, List, Optional
import os
import openai
import logging
import base64
import tempfile
from pydantic import BaseModel

from .adapters import BaseSTTAdapter, BaseTTSAdapter

logger = logging.getLogger(__name__)

class OpenAIWhisperAdapter(BaseSTTAdapter):
    """Speech-to-Text adapter using OpenAI's Whisper API."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "whisper-1"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        self.model = model
        openai.api_key = self.api_key

    def recognize(self, audio_data: Any) -> Optional[str]:
        try:
            # Save audio data to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name

            with open(temp_path, "rb") as audio_file:
                response = openai.Audio.transcribe(
                    model=self.model,
                    file=audio_file
                )
            
            os.unlink(temp_path)  # Clean up temp file
            return response["text"]
        except Exception as e:
            logger.exception("Error in Whisper transcription")
            return None


class OpenAITTSAdapter(BaseTTSAdapter):
    """Text-to-Speech adapter using OpenAI's TTS API."""
    
    def __init__(self, api_key: Optional[str] = None, voice: str = "alloy"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        self.voice = voice
        openai.api_key = self.api_key

    def synthesize(self, text: str) -> str:
        try:
            response = openai.Audio.create(
                model="tts-1",
                voice=self.voice,
                input=text
            )

            # Save audio to temp file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_file.write(response.content)
            temp_file.close()
            return temp_file.name
        except Exception as e:
            logger.exception("Error in TTS generation")
            raise


class ChatMessage(BaseModel):
    """Schema for chat messages."""
    role: str
    content: str


class BaseLLMAdapter:
    """Base class for Language Model adapters."""
    
    def chat_completion(self, messages: List[ChatMessage], **kwargs) -> Optional[str]:
        """Get chat completion from the LLM."""
        raise NotImplementedError()


class OpenAILLMAdapter(BaseLLMAdapter):
    """Language Model adapter using OpenAI's GPT API."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        self.model = model
        openai.api_key = self.api_key

    def chat_completion(self, messages: List[ChatMessage], **kwargs) -> Optional[str]:
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[msg.dict() for msg in messages],
                **kwargs
            )
            return response.choices[0].message['content'].strip()
        except Exception as e:
            logger.exception("Error in chat completion")
            return None


def get_llm_adapter() -> BaseLLMAdapter:
    """Factory to select LLM adapter via environment variable LLM_PROVIDER."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "openai":
        return OpenAILLMAdapter()
    logger.warning("LLM provider %s not implemented, falling back to OpenAI", provider)
    return OpenAILLMAdapter()