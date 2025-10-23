import pytest
from src.agent.call_handler import CallHandler
from unittest.mock import patch, MagicMock, AsyncMock
import os

@pytest.fixture
def call_handler():
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
        handler = CallHandler()
        # Initialize conversation history with system prompt
        assert len(handler.conversation_history) == 1
        assert handler.conversation_history[0]['role'] == 'system'
        return handler

@pytest.fixture
def mock_audio_data():
    return MagicMock()

@pytest.mark.asyncio
async def test_process_call_success(call_handler, mock_audio_data):
    # Mock speech recognition
    with patch.object(call_handler.speech_recognition, 'recognize_from_audio') as mock_recognize:
        mock_recognize.return_value = "Hello, I need help with my internet connection"
        
        # Mock OpenAI response
        mock_openai_response = MagicMock()
        mock_openai_response.choices = [
            MagicMock(message={'content': 'I understand you\'re having internet issues. Let me help.'})
        ]
        
        with patch('openai.ChatCompletion.create', return_value=mock_openai_response):
            # Mock TTS
            with patch.object(call_handler.tts_engine, 'text_to_speech') as mock_tts:
                mock_tts.return_value = '/path/to/audio.mp3'
                
                response = await call_handler.process_call(mock_audio_data)
                
                assert response['status'] == 'success'
                assert 'internet issues' in response['message']
                assert response['audio_path'] == '/path/to/audio.mp3'
                
                # Verify conversation history was updated correctly
                assert len(call_handler.conversation_history) == 3  # system + user + assistant
                assert call_handler.conversation_history[-2]['role'] == 'user'
                assert call_handler.conversation_history[-2]['content'] == "Hello, I need help with my internet connection"
                assert call_handler.conversation_history[-1]['role'] == 'assistant'
                assert call_handler.conversation_history[-1]['content'] == response['message']

@pytest.mark.asyncio
async def test_process_call_speech_recognition_failure(call_handler, mock_audio_data):
    with patch.object(call_handler.speech_recognition, 'recognize_from_audio') as mock_recognize:
        mock_recognize.return_value = None
        
        response = await call_handler.process_call(mock_audio_data)
        
        assert response['status'] == 'error'
        assert response['message'] == 'Could not understand audio'
        assert response['audio_path'] is None
        
        # Verify conversation history wasn't updated
        assert len(call_handler.conversation_history) == 1  # only system prompt

@pytest.mark.asyncio
async def test_get_ai_response(call_handler):
    test_response = 'This is a test response'
    mock_openai_response = MagicMock()
    mock_openai_response.choices = [
        MagicMock(message={'content': test_response})
    ]
    
    with patch('openai.ChatCompletion.create', return_value=mock_openai_response) as mock_create:
        response = await call_handler.get_ai_response()
        
        assert response == test_response
        # Verify OpenAI API was called with correct parameters
        mock_create.assert_called_once_with(
            model="gpt-3.5-turbo",
            messages=call_handler.conversation_history,
            max_tokens=150,
            temperature=0.7
        )
        assert len(call_handler.conversation_history) == 2  # system + assistant

@pytest.mark.asyncio
async def test_process_call_ai_error(call_handler, mock_audio_data):
    with patch.object(call_handler.speech_recognition, 'recognize_from_audio') as mock_recognize:
        mock_recognize.return_value = "Hello, I need help"
        
        with patch('openai.ChatCompletion.create', side_effect=Exception("API Error")):
            response = await call_handler.process_call(mock_audio_data)
            
            assert response['status'] == 'error'
            assert 'API Error' in response['message']
            assert response['audio_path'] is None

@pytest.mark.asyncio
async def test_conversation_history_limit(call_handler):
    # Test that conversation history maintains reasonable size
    mock_openai_response = MagicMock()
    mock_openai_response.choices = [
        MagicMock(message={'content': 'Response'})
    ]
    
    with patch('openai.ChatCompletion.create', return_value=mock_openai_response):
        # Simulate 10 exchanges
        for _ in range(10):
            await call_handler.get_ai_response()
        
        # Verify history size is reasonable (system + 10 exchanges)
        assert len(call_handler.conversation_history) <= 21