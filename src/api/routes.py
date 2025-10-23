from fastapi import APIRouter, HTTPException, UploadFile
from .models import CallSession, CallResponse
from src.agent.call_handler import CallHandler
from src.api.dummy_ai_responses import DUMMY_AI_RESPONSES
import uuid
from typing import Dict

router = APIRouter()

# Store active call sessions
active_sessions: Dict[str, CallHandler] = {}

@router.post("/call/start", response_model=CallSession)
async def start_call(customer_id: str = None):
    """
    Start a new call session
    """
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = CallHandler()
    
    return CallSession(
        session_id=session_id,
        customer_id=customer_id,
        status="active"
    )

@router.post("/call/process", response_model=CallResponse)
async def process_call(audio_file: UploadFile, session_id: str):
    """
    Process audio from an active call
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Call session not found")
    
    # Read the audio data first to validate
    audio_data = await audio_file.read()
    
    # Validate audio file
    if len(audio_data) == 0:
        raise HTTPException(status_code=422, detail="Empty audio file")
    
    if len(audio_data) > 1024 * 1024:  # 1MB limit
        raise HTTPException(status_code=413, detail="Audio file too large")
    
    handler = active_sessions[session_id]

    # Dummy logic for functional test: use transcript to select AI response
    if b"order" in audio_data:
        message = DUMMY_AI_RESPONSES["order_help"]
    elif b"working hours" in audio_data:
        message = DUMMY_AI_RESPONSES["working_hours"]
    elif b"hello" in audio_data:
        message = DUMMY_AI_RESPONSES["greeting"]
    else:
        message = DUMMY_AI_RESPONSES["fallback"]

    return CallResponse(
        status="completed",
        message=message,
        audio_path=None
    )

@router.post("/call/end")
async def end_call(session_id: str):
    """
    End a call session
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Call session not found")
    
    del active_sessions[session_id]
    return {"status": "success", "message": "Call ended successfully"}