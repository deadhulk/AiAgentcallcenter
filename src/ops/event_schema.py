from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import time


class OrchestrationEvent(BaseModel):
    # high-level event type (call.created, call.answered, call.ended, etc.)
    event_type: str
    # epoch seconds
    timestamp: int = Field(default_factory=lambda: int(time.time()))

    # FreeSWITCH specifics
    fs_event: Optional[str] = None
    uuid: Optional[str] = None

    # Caller / callee
    caller_number: Optional[str] = None
    caller_name: Optional[str] = None
    callee: Optional[str] = None

    # call lifecycle
    call_state: Optional[str] = None
    call_direction: Optional[str] = None
    hangup_cause: Optional[str] = None
    hangup_cause_code: Optional[str] = None
    duration_seconds: Optional[int] = None

    # raw event for debugging
    raw_headers: Optional[Dict[str, Any]] = None
    raw_body: Optional[str] = None

    # full payload (duplicate of other fields in structured form)
    payload: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True
