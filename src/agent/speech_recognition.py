import speech_recognition as sr
from typing import Optional

class SpeechRecognitionEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def recognize_from_audio(self, audio_data) -> Optional[str]:
        """
        Convert audio data to text using Google Speech Recognition
        """
        try:
            text = self.recognizer.recognize_google(audio_data)
            return text
        except sr.UnknownValueError:
            return None
        except sr.RequestError:
            return None