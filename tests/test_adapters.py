"""Tests for speech/LLM adapters"""
import pytest
from unittest.mock import Mock, patch
from src.agent.adapters import (
    BaseSTTAdapter,
    BaseTTSAdapter,
    get_stt_adapter,
    get_tts_adapter,
    get_llm_adapter
)
from src.agent.openai_adapters import (
    OpenAIWhisperAdapter,
    OpenAITTSAdapter,
    OpenAILLMAdapter,
    ChatMessage,
    BaseLLMAdapter
)
from src.agent.aws_adapters import AWSTranscribeAdapter, AWSPollyAdapter


def test_stt_adapter_factory():
    """Test STT adapter factory with different providers"""
    # Test mock adapter (default)
    with patch.dict('os.environ', {'STT_PROVIDER': 'mock'}):
        adapter = get_stt_adapter()
        assert isinstance(adapter, BaseSTTAdapter)

    # Test OpenAI Whisper adapter
    with patch.dict('os.environ', {
        'STT_PROVIDER': 'whisper',
        'OPENAI_API_KEY': 'test_key'
    }):
        adapter = get_stt_adapter()
        assert isinstance(adapter, OpenAIWhisperAdapter)

    # Test AWS adapter
    with patch.dict('os.environ', {
        'STT_PROVIDER': 'aws',
        'AWS_ACCESS_KEY_ID': 'test_key',
        'AWS_SECRET_ACCESS_KEY': 'test_secret'
    }):
        adapter = get_stt_adapter()
        assert isinstance(adapter, AWSTranscribeAdapter)


def test_tts_adapter_factory():
    """Test TTS adapter factory with different providers"""
    # Test gTTS adapter (default)
    with patch.dict('os.environ', {'TTS_PROVIDER': 'gtts'}):
        adapter = get_tts_adapter()
        assert isinstance(adapter, BaseTTSAdapter)

    # Test OpenAI TTS adapter
    with patch.dict('os.environ', {
        'TTS_PROVIDER': 'openai',
        'OPENAI_API_KEY': 'test_key'
    }):
        adapter = get_tts_adapter()
        assert isinstance(adapter, OpenAITTSAdapter)

    # Test AWS Polly adapter
    with patch.dict('os.environ', {
        'TTS_PROVIDER': 'polly',
        'AWS_ACCESS_KEY_ID': 'test_key',
        'AWS_SECRET_ACCESS_KEY': 'test_secret'
    }):
        adapter = get_tts_adapter()
        assert isinstance(adapter, AWSPollyAdapter)


def test_llm_adapter():
    """Test LLM adapter with OpenAI"""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
        adapter = get_llm_adapter()
        assert isinstance(adapter, BaseLLMAdapter)

        # Test chat completion
        messages = [
            ChatMessage(role="system", content="You are a test assistant"),
            ChatMessage(role="user", content="Hello")
        ]

        with patch('openai.ChatCompletion.create') as mock_create:
            mock_create.return_value.choices = [
                Mock(message={'content': 'Hello! How can I help?'})
            ]

            response = adapter.chat_completion(messages)
            assert response == "Hello! How can I help?"
            mock_create.assert_called_once()


def test_openai_whisper_adapter():
    """Test OpenAI Whisper adapter"""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
        adapter = OpenAIWhisperAdapter()
        
        with patch('openai.Audio.transcribe') as mock_transcribe:
            mock_transcribe.return_value = {"text": "Hello world"}
            
            result = adapter.recognize(b"test audio data")
            assert result == "Hello world"
            mock_transcribe.assert_called_once()


def test_openai_tts_adapter():
    """Test OpenAI TTS adapter"""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
        adapter = OpenAITTSAdapter()
        
        with patch('openai.Audio.create') as mock_create:
            mock_create.return_value.content = b"test audio data"
            
            path = adapter.synthesize("Hello world")
            assert path.endswith('.mp3')
            mock_create.assert_called_once()


def test_aws_transcribe_adapter():
    """Test AWS Transcribe adapter"""
    with patch.dict('os.environ', {
        'AWS_ACCESS_KEY_ID': 'test_key',
        'AWS_SECRET_ACCESS_KEY': 'test_secret',
        'AWS_S3_BUCKET': 'test-bucket'
    }):
        def fake_getenv(key, default=None):
            env = {
                'AWS_ACCESS_KEY_ID': 'test_key',
                'AWS_SECRET_ACCESS_KEY': 'test_secret',
                'AWS_S3_BUCKET': 'test-bucket',
            }
            return env.get(key, default)
        with patch('src.agent.aws_adapters.boto3.client') as mock_client, \
             patch('src.agent.aws_adapters.tempfile.NamedTemporaryFile') as mock_tempfile, \
             patch('src.agent.aws_adapters.os.unlink'), \
             patch('src.agent.aws_adapters.os.getenv', side_effect=fake_getenv), \
             patch('urllib.request.urlopen') as mock_urlopen:
            mock_transcribe = Mock()
            mock_s3 = Mock()
            mock_client.side_effect = [mock_transcribe, mock_s3]
            # Mock temp file
            from unittest.mock import MagicMock
            mock_temp = MagicMock()
            mock_temp.__enter__.return_value = mock_temp
            mock_temp.name = 'temp.wav'
            mock_tempfile.return_value = mock_temp
            # Mock transcription job status
            mock_transcribe.get_transcription_job.return_value = {
                'TranscriptionJob': {
                    'TranscriptionJobStatus': 'COMPLETED',
                    'Transcript': {
                        'TranscriptFileUri': 'https://test.com/transcript.json'
                    }
                }
            }
            # Mock urllib request
            mock_response = Mock()
            mock_response.read.return_value = b'{"results":{"transcripts":[{"transcript":"Hello world"}]}}'
            mock_urlopen.return_value = mock_response
            adapter = AWSTranscribeAdapter()
            result = adapter.recognize(b"test audio data")
            assert result == "Hello world"


def test_aws_polly_adapter():
    """Test AWS Polly adapter"""
    with patch.dict('os.environ', {
        'AWS_ACCESS_KEY_ID': 'test_key',
        'AWS_SECRET_ACCESS_KEY': 'test_secret'
    }):
        with patch('src.agent.aws_adapters.boto3.client') as mock_client, \
             patch('src.agent.aws_adapters.tempfile.NamedTemporaryFile') as mock_tempfile:
            mock_polly = Mock()
            mock_client.return_value = mock_polly
            mock_stream = Mock()
            mock_stream.read.return_value = b"test audio data"
            mock_polly.synthesize_speech.return_value = {
                'AudioStream': mock_stream
            }
            # Mock temp file
            from unittest.mock import MagicMock
            mock_temp = MagicMock()
            mock_temp.__enter__.return_value = mock_temp
            mock_temp.name = 'temp.mp3'
            mock_tempfile.return_value = mock_temp
            adapter = AWSPollyAdapter()
            path = adapter.synthesize("Hello world")
            assert path.endswith('.mp3')
            mock_polly.synthesize_speech.assert_called_once()