from pydantic import BaseModel
from typing import Optional

class CallSession(BaseModel):
    session_id: str
    customer_id: Optional[str] = None
    status: str

class AudioInput(BaseModel):
    session_id: str
    audio_data: bytes

class CallResponse(BaseModel):
    status: str
    message: str
    audio_path: Optional[str] = None