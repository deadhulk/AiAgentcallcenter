from gtts import gTTS
import tempfile
import os

class TTSEngine:
    def __init__(self):
        self.language = 'en'

    def text_to_speech(self, text: str) -> str:
        """
        Convert text to speech and save as temporary audio file
        Returns the path to the generated audio file
        """
        tts = gTTS(text=text, lang=self.language, slow=False)
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_file_path = temp_file.name
        temp_file.close()
        
        # Save the speech to the temporary file
        tts.save(temp_file_path)
        
        return temp_file_path

    def cleanup_audio_file(self, file_path: str):
        """
        Remove temporary audio file
        """
        if os.path.exists(file_path):
            os.remove(file_path)