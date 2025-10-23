"""AWS adapters for STT and TTS services using Amazon Transcribe and Polly."""
from typing import Any, Optional
import os
import boto3
import tempfile
import logging
from .adapters import BaseSTTAdapter, BaseTTSAdapter

logger = logging.getLogger(__name__)

class AWSTranscribeAdapter(BaseSTTAdapter):
    """Speech-to-Text adapter using Amazon Transcribe."""
    
    def __init__(self, 
                 aws_access_key: Optional[str] = None,
                 aws_secret_key: Optional[str] = None,
                 region: str = "us-east-1"):
        self.aws_access_key = aws_access_key or os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = aws_secret_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        if not (self.aws_access_key and self.aws_secret_key):
            raise ValueError("AWS credentials not provided")
        
        self.client = boto3.client(
            'transcribe',
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
            region_name=region
        )
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
            region_name=region
        )

    def recognize(self, audio_data: Any) -> Optional[str]:
        try:
            # Save audio to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name

            # Upload to S3 (requires a bucket)
            bucket = os.getenv("AWS_S3_BUCKET")
            key = f"transcribe/input/{os.path.basename(temp_path)}"
            self.s3.upload_file(temp_path, bucket, key)
            
            # Start transcription job
            job_name = f"transcribe-{os.path.basename(temp_path)}"
            self.client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': f"s3://{bucket}/{key}"},
                MediaFormat='wav',
                LanguageCode='en-US'
            )

            # Wait for completion
            import time
            while True:
                status = self.client.get_transcription_job(TranscriptionJobName=job_name)
                if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
                    break
                time.sleep(1)

            if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
                import urllib.request
                import json
                transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
                response = urllib.request.urlopen(transcript_uri)
                data = json.loads(response.read())
                return data['results']['transcripts'][0]['transcript']

            return None
        except Exception:
            logger.exception("Error in AWS transcription")
            return None
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass


class AWSPollyAdapter(BaseTTSAdapter):
    """Text-to-Speech adapter using Amazon Polly."""
    
    def __init__(self,
                 aws_access_key: Optional[str] = None,
                 aws_secret_key: Optional[str] = None,
                 region: str = "us-east-1",
                 voice_id: str = "Joanna"):
        self.aws_access_key = aws_access_key or os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = aws_secret_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        if not (self.aws_access_key and self.aws_secret_key):
            raise ValueError("AWS credentials not provided")

        self.client = boto3.client(
            'polly',
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
            region_name=region
        )
        self.voice_id = voice_id

    def synthesize(self, text: str) -> str:
        try:
            response = self.client.synthesize_speech(
                Text=text,
                OutputFormat='mp3',
                VoiceId=self.voice_id,
                Engine='neural'
            )

            # Save audio stream to temp file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_file.write(response['AudioStream'].read())
            temp_file.close()
            return temp_file.name
        except Exception:
            logger.exception("Error in Polly synthesis")
            raise