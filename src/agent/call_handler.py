import openai
from typing import Dict, Any
import os
from .speech_recognition import SpeechRecognitionEngine
from .tts_engine import TTSEngine

class CallHandler:
    def __init__(self):
        self.speech_recognition = SpeechRecognitionEngine()
        self.tts_engine = TTSEngine()
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        # Initial system prompt to set the AI's role
        self.conversation_history = [{
            "role": "system",
            "content": """You are a professional call center agent for a telecommunications company. 
            You are helpful, polite, and efficient. You can handle customer inquiries about:
            - Technical support
            - Billing issues
            - Service upgrades
            - Network problems
            Always maintain a professional tone and follow proper call center protocols."""
        }]

    async def process_call(self, audio_data: Any) -> Dict[str, str]:
        """
        Process incoming call audio and return appropriate response
        """
        # Convert speech to text
        user_text = self.speech_recognition.recognize_from_audio(audio_data)
        if not user_text:
            return {
                "status": "error",
                "message": "Could not understand audio",
                "audio_path": None
            }

        # Add user message to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_text
        })

        # Get AI response
        try:
            response = await self.get_ai_response()
            
            # Convert response to speech
            audio_path = self.tts_engine.text_to_speech(response)

            return {
                "status": "success",
                "message": response,
                "audio_path": audio_path
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "audio_path": None
            }

    async def get_ai_response(self) -> str:
        """
        Get response from OpenAI API
        """
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=self.conversation_history,
                max_tokens=150,
                temperature=0.7
            )
            
            ai_message = response.choices[0].message['content'].strip()
            
            # Add AI response to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": ai_message
            })
            
            return ai_message
        except Exception as e:
            raise Exception(f"Error getting AI response: {str(e)}")