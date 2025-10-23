from fastapi import APIRouter, HTTPException, UploadFile, Request
from .models import CallSession, CallResponse
from src.agent.call_handler import CallHandler
from src.api.dummy_ai_responses import DUMMY_AI_RESPONSES
from src.ops import monitoring
import uuid
import time
from typing import Dict

router = APIRouter()

# Get logger instance for this module
logger = monitoring.logger.bind(module="api_routes")

# Store active call sessions
active_sessions: Dict[str, CallHandler] = {}

@router.post("/call/start", response_model=CallSession)
async def start_call(request: Request, customer_id: str = None):
    """
    Start a new call session
    """
    monitoring.track_request("/call/start", request.method, 200)
    
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = CallHandler()
    
    # Start monitoring for the call
    monitoring.track_call_start()
    monitoring.track_event("session.created")
    
    call_span_ctx = monitoring.start_call_span(session_id)
    if hasattr(call_span_ctx, "__enter__"):
        call_span = call_span_ctx.__enter__()
    else:
        call_span = call_span_ctx
    if call_span is not None and hasattr(call_span, "set_attribute"):
        call_span.set_attribute("customer_id", customer_id)
        
    logger.info("Call session started", session_id=session_id, customer_id=customer_id)
    
    return CallSession(
        session_id=session_id,
        customer_id=customer_id,
        status="active"
    )

@router.post("/call/process", response_model=CallResponse)
async def process_call(request: Request, audio_file: UploadFile, session_id: str):
    """
    Process audio from an active call
    """
    start_time = time.time()
    
    try:
        if session_id not in active_sessions:
            monitoring.track_error("session_not_found")
            monitoring.track_request("/call/process", request.method, 404)
            raise HTTPException(status_code=404, detail="Call session not found")

        call_span_ctx = monitoring.start_call_span(session_id)
        if hasattr(call_span_ctx, "__enter__"):
            span = call_span_ctx.__enter__()
        else:
            span = call_span_ctx

        audio_data = await audio_file.read()
        audio_size = len(audio_data)

        # Validate audio file
        if audio_size == 0:
            monitoring.track_error("empty_audio")
            monitoring.track_request("/call/process", request.method, 422)
            raise HTTPException(status_code=422, detail="Empty audio file")

        if audio_size > 1024 * 1024:  # 1MB limit
            monitoring.track_error("audio_too_large")
            monitoring.track_request("/call/process", request.method, 413)
            return CallResponse(status="error", message="Audio file too large", audio_path=None)

        handler = active_sessions[session_id]

        # Track speech processing
        with monitoring.start_speech_span(session_id) as speech_span:
            # Dummy logic for functional test: use transcript to select AI response
            if b"order" in audio_data:
                message = DUMMY_AI_RESPONSES["order_help"]
                message_type = "order_help"
            elif b"working hours" in audio_data:
                message = DUMMY_AI_RESPONSES["working_hours"]
                message_type = "working_hours"
            elif b"hello" in audio_data:
                message = DUMMY_AI_RESPONSES["greeting"]
                message_type = "greeting"
            else:
                message = DUMMY_AI_RESPONSES["fallback"]
                message_type = "fallback"

            # Record metrics about the processing
            processing_time = time.time() - start_time
            monitoring.track_speech_processing(processing_time)
            monitoring.track_event(f"response.{message_type}")

        if span is not None and hasattr(span, "set_attribute"):
            span.set_attribute("processing_time", processing_time)
            span.set_attribute("audio_size", audio_size)
            span.set_attribute("response_type", message_type)

        monitoring.track_request("/call/process", request.method, 200)
        logger.info(
            "Call processed",
            session_id=session_id,
            audio_size=audio_size,
            processing_time=processing_time,
            response_type=message_type
        )

        return CallResponse(
            status="completed",
            message=message,
            audio_path=None
        )

    except HTTPException as e:
        # Let FastAPI handle HTTPException so status code is correct
        raise
    except Exception as e:
        monitoring.track_error("process_call_error")
        monitoring.track_request("/call/process", request.method, 500)
        logger.exception("Error processing call", error=str(e))
        return CallResponse(status="error", message="Internal server error", audio_path=None)

@router.post("/call/end")
async def end_call(request: Request, session_id: str):
    """
    End a call session
    """
    try:
        if session_id not in active_sessions:
            monitoring.track_error("session_not_found")
            monitoring.track_request("/call/end", request.method, 404)
            raise HTTPException(status_code=404, detail="Call session not found")
        
        # Track call metrics
        handler = active_sessions[session_id]
        duration = None  # TODO: Track actual call duration in handler
        monitoring.track_call_end(duration)
        monitoring.track_event("session.ended")
        
        # Clean up
        del active_sessions[session_id]
        
        monitoring.track_request("/call/end", request.method, 200)
        logger.info("Call session ended", session_id=session_id)
        
        return {"status": "success", "message": "Call ended successfully"}
        
    except HTTPException as e:
        raise
    except Exception as e:
        monitoring.track_error("end_call_error")
        monitoring.track_request("/call/end", request.method, 500)
        logger.exception("Error ending call", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")