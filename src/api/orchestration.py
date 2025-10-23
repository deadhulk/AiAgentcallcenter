from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, AnyHttpUrl
from typing import List, Optional, Dict, Any
import uuid

from src.ops import orchestration

router = APIRouter()


class RegisterEndpointRequest(BaseModel):
    url: AnyHttpUrl
    events: Optional[List[str]] = None


class EndpointResponse(BaseModel):
    id: str
    url: AnyHttpUrl
    events: List[str]


@router.get("/endpoints", response_model=List[EndpointResponse])
async def list_endpoints(request: Request):
    app = request.app
    endpoints = getattr(app.state, "workflow_endpoints", [])
    return endpoints


@router.post("/endpoints", response_model=EndpointResponse)
async def register_endpoint(req: RegisterEndpointRequest, request: Request):
    app = request.app
    endpoint_id = str(uuid.uuid4())
    events = req.events or ["*"]
    ep = orchestration.register_workflow_endpoint(app, endpoint_id, str(req.url), events)
    return ep


@router.delete("/endpoints/{endpoint_id}")
async def unregister_endpoint(endpoint_id: str, request: Request):
    app = request.app
    removed = orchestration.unregister_workflow_endpoint(app, endpoint_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return {"status": "ok", "removed": endpoint_id}


@router.post("/emit/{event_type}")
async def emit_event(event_type: str, payload: Dict[str, Any], request: Request):
    """Emit a test event to registered endpoints. Payload will be forwarded as-is.

    This is useful for testing n8n/workflow integration.
    """
    app = request.app
    results = await orchestration.emit_event(app, event_type, payload)
    return {"dispatched": len(results), "results": results}
