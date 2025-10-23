from typing import Any, Dict, List, Optional
import asyncio
import json
import os
from datetime import datetime

import httpx
from . import monitoring
from src.ops.event_schema import OrchestrationEvent
from src.ops.crm import get_crm_adapter, CRMCallData


logger = monitoring.logger.bind(module="orchestration")


class OrchestrationError(Exception):
    pass


def init_orchestration(app: Any):
    """Initialize orchestration hooks: webhook registry, SIP bridge stubs, etc.

    Attaches a lightweight webhook registry to `app.state.workflow_endpoints` so
    other parts of the system can register workflow endpoints (n8n, Zapier,
    custom workflow engines) to receive call events.
    """
    logger.info("Initializing orchestration hooks (webhook registry / SIP bridge)")
    
    # Initialize metrics
    monitoring.ACTIVE_CALLS.set(0)
    monitoring.QUEUE_SIZE.labels(queue="esl").set(0)
    monitoring.QUEUE_SIZE.labels(queue="speech").set(0)
    monitoring.QUEUE_SIZE.labels(queue="crm").set(0)
    
    # webhook endpoints will be a list of dicts: {"id": str, "url": str, "events": [..]}
    app.state.workflow_endpoints = []
    
    # Initialize CRM adapter if configured
    app.state.crm_adapter = None
    try:
        app.state.crm_adapter = get_crm_adapter()
        logger.info("CRM adapter initialized")
    except Exception:
        logger.exception("Failed to initialize CRM adapter")
    
    # Track active calls for CRM integration
    app.state.active_calls = {}
    
    # capture the current event loop so background threads (ESL) can schedule
    # coroutine dispatches back into the FastAPI loop.
    try:
        app.state.event_loop = asyncio.get_running_loop()
    except RuntimeError:
        app.state.event_loop = None
        
    # instantiate SIP bridge if environment requests it
    app.state.sip_bridge = None
    try:
            if os.getenv("ENABLE_FREESWITCH_BRIDGE", "false").lower() in ("1", "true", "yes"):
                # Start the enhanced ESL connector with LiveKit bridging
                from src.ops.sip_bridge_esl import SIPBridgeConnector

                def _on_esl_event(evt):
                    # Map FreeSWITCH ESL event to a richer internal schema and dispatch
                    headers = evt.get("headers", {}) if isinstance(evt, dict) else {}
                    event_name = headers.get("Event-Name") or headers.get("event-name")
                    fs_uuid = headers.get("Unique-ID") or headers.get("unique-id")
                    caller_number = headers.get("Caller-Caller-ID-Number") or headers.get("Caller-ID-Number") or headers.get("caller-caller-id-number")
                    caller_name = headers.get("Caller-Caller-ID-Name") or headers.get("Caller-ID-Name")
                    callee = headers.get("Caller-Destination-Number") or headers.get("Destination-Number") or headers.get("destination-number")

                    # derive some higher-level fields
                    call_state = headers.get("Channel-Call-State") or headers.get("Channel-Call-State".lower())
                    hangup_cause = headers.get("Hangup-Cause") or headers.get("hangup-cause")
                    hangup_cause_code = headers.get("Hangup-Cause-Code") or headers.get("hangup-cause-code")

                    duration = None
                    try:
                        if "Variable_call_duration" in headers:
                            duration = int(headers.get("Variable_call_duration"))
                        elif "Duration" in headers:
                            duration = int(headers.get("Duration"))
                    except Exception:
                        duration = None

                    # interpret event -> normalized event_type
                    if event_name == "CHANNEL_CREATE":
                        event_type = "call.created"
                    elif event_name == "CHANNEL_ANSWER":
                        event_type = "call.answered"
                    elif event_name in ("CHANNEL_HANGUP", "CHANNEL_DESTROY", "HANGUP"):
                        event_type = "call.ended"
                    else:
                        event_type = f"fs.{event_name.lower()}" if event_name else "fs.unknown"

                    enriched = OrchestrationEvent(
                        event_type=event_type,
                        fs_event=event_name,
                        uuid=fs_uuid,
                        caller_number=caller_number,
                        caller_name=caller_name,
                        callee=callee,
                        call_state=call_state,
                        hangup_cause=hangup_cause,
                        hangup_cause_code=hangup_cause_code,
                        duration_seconds=duration,
                        raw_headers=headers,
                        raw_body=evt.get("body") if isinstance(evt, dict) else None,
                        payload={
                            "headers": headers, 
                            "body": evt.get("body") if isinstance(evt, dict) else None,
                            "livekit_room": f"call-{fs_uuid}" if fs_uuid else None
                        },
                    )

                    logger.info("ESL event mapped and enriched: %s -> %s", event_name, event_type)

                    # dispatch into the FastAPI loop thread-safely
                    loop = getattr(app.state, "event_loop", None)
                    if loop is None:
                        logger.warning("No event loop available on app.state, skipping emit_event")
                        return
                    try:
                        asyncio.run_coroutine_threadsafe(emit_event(app, enriched.event_type, enriched.dict()), loop)
                    except Exception:
                        logger.exception("Failed to schedule emit_event for ESL event")

                connector = SIPBridgeConnector(
                    host=os.getenv("FREESWITCH_HOST", "freeswitch"),
                    port=int(os.getenv("FREESWITCH_ESL_PORT", 8021)),
                    password=os.getenv("FREESWITCH_ESL_PASSWORD", "ClueCon"),
                    on_event=_on_esl_event
                )
                connector.start()
                app.state.sip_bridge = connector
                logger.info("SIP-LiveKit bridge connector started")
    except Exception:
        logger.exception("Failed to start SIP-LiveKit bridge connector")
def shutdown_orchestration(app: Any):
    """Cleanly shutdown orchestration components"""
    logger.info("Shutting down orchestration hooks")
    
    # Clean up SIP bridge
    if getattr(app.state, "sip_bridge", None):
        try:
            app.state.sip_bridge.shutdown()
        except Exception:
            logger.exception("Error while shutting down SIP bridge")
            
    # Push any remaining active calls to CRM
    if getattr(app.state, "crm_adapter", None) and getattr(app.state, "active_calls", None):
        loop = asyncio.get_event_loop()
        for call_id, call_data in app.state.active_calls.items():
            if not call_data.get("end_time"):
                call_data["end_time"] = datetime.utcnow()
                try: # Log final call state to CRM
                    loop.run_until_complete(app.state.crm_adapter.log_call(
                        CRMCallData(**call_data)
                    ))
                except Exception as e:
                    # Log error but continue trying to shut down other calls
                    logger.exception("Error logging final call state to CRM")


async def _dispatch_to_endpoint(client: httpx.AsyncClient, endpoint: Dict[str, Any], payload: Dict[str, Any]):
    """Send payload to single endpoint and return result dict."""
    url = endpoint.get("url")
    headers = {"Content-Type": "application/json"}
    event_type = payload.get("event", "unknown")
    
    monitoring.track_event("webhook_dispatch_attempt")
    monitoring.QUEUE_SIZE.labels(queue="webhook").inc()
    
    try:
        with monitoring.start_span("webhook_dispatch") as span_ctx:
            span = getattr(span_ctx, "__enter__", None)
            if span is not None:
                # If using a context manager, get the span from __enter__
                span = span_ctx.__enter__()
            else:
                span = span_ctx
            if span is not None and hasattr(span, "set_attribute"):
                span.set_attribute("endpoint_url", url)
                span.set_attribute("event_type", event_type)
            resp = await client.post(url, content=json.dumps(payload), headers=headers, timeout=10.0)
            logger.debug("Dispatched event to %s, status=%s", url, resp.status_code)
            if span is not None and hasattr(span, "set_attribute"):
                span.set_attribute("status_code", resp.status_code)
            if not resp.is_success:
                monitoring.track_error("webhook_dispatch_failure")
            return {"url": url, "status_code": resp.status_code, "ok": resp.is_success}
    except Exception as exc:
        logger.exception("Error dispatching to %s", url)
        monitoring.track_error("webhook_dispatch_error")
        return {"url": url, "status_code": None, "ok": False, "error": str(exc)}
    finally:
        monitoring.QUEUE_SIZE.labels(queue="webhook").dec()


async def emit_event(app: Any, event_type: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Emit an event to all registered workflow endpoints and the CRM that subscribed to it.

    Returns a list of dispatch results for observability.
    """
    monitoring.track_event(f"event.emit.{event_type}")
    
    # Handle call lifecycle events for CRM integration
    crm = getattr(app.state, "crm_adapter", None)
    active_calls = getattr(app.state, "active_calls", {})
    
    if crm and event_type.startswith("call."):
        uuid = payload.get("uuid")
        if uuid:
            if event_type == "call.created":
                # Start tracking new call
                start_time = datetime.utcnow()
                active_calls[uuid] = {
                    "call_id": uuid,
                    "customer_id": payload.get("caller_number"),
                    "start_time": start_time,
                    "metadata": payload
                }
                
                # Initialize monitoring
                monitoring.track_call_start()
                call_span_ctx = monitoring.start_call_span(uuid)
                if hasattr(call_span_ctx, "__enter__"):
                    call_span = call_span_ctx.__enter__()
                else:
                    call_span = call_span_ctx
                if call_span is not None and hasattr(call_span, "set_attribute"):
                    call_span.set_attribute("customer_id", payload.get("caller_number"))
                    call_span.set_attribute("start_time", start_time.isoformat())
                    logger.info("Call tracing initialized", call_id=uuid)
                
            elif event_type == "call.ended":
                # Update and push final call state to CRM
                if uuid in active_calls:
                    call_data = active_calls[uuid]
                    end_time = datetime.utcnow()
                    call_data["end_time"] = end_time
                    duration_seconds = None
                    
                    if "duration_seconds" in payload:
                        duration_seconds = payload["duration_seconds"]
                        call_data["duration_seconds"] = duration_seconds
                    
                    # Get transcript if available
                    transcript = None
                    if payload.get("raw_headers", {}).get("variable_call_transcript"):
                        transcript = payload["raw_headers"]["variable_call_transcript"]
                    call_data["transcript"] = transcript
                    
                    crm_span_ctx = monitoring.start_span(name="crm_log_call")
                    if hasattr(crm_span_ctx, "__enter__"):
                        crm_span = crm_span_ctx.__enter__()
                    else:
                        crm_span = crm_span_ctx
                    try:
                        # Log to CRM
                        await crm.log_call(CRMCallData(**call_data))
                        # Track metrics for completed call
                        monitoring.track_call_end(duration_seconds)
                        monitoring.track_event("call.crm_logged")
                        if crm_span is not None and hasattr(crm_span, "set_attribute"):
                            crm_span.set_attribute("call_id", uuid)
                            crm_span.set_attribute("duration_seconds", duration_seconds)
                    except Exception as e:
                        logger.exception("Error logging call to CRM")
                        monitoring.track_error("crm_log_failure")
                        if crm_span is not None and hasattr(crm_span, "set_status"):
                            monitoring.record_error(crm_span, e)
                    finally:
                        # Clean up tracking
                        del active_calls[uuid]

    # Process webhook endpoints
    endpoints: List[Dict[str, Any]] = getattr(app.state, "workflow_endpoints", []) or []
    # filter endpoints by event subscription (wildcard '*' subscribes to all)
    targets = [e for e in endpoints if "*" in e.get("events", []) or event_type in e.get("events", [])]
    if not targets:
        logger.info("No workflow endpoints registered for event %s", event_type)
        return []
    
    payload_envelope = {
        "event": event_type,
        "timestamp": int(datetime.utcnow().timestamp()),
        "payload": payload,
    }

    monitoring.QUEUE_SIZE.labels(queue="webhook").inc()
    async with httpx.AsyncClient() as client:
        tasks = [_dispatch_to_endpoint(client, ep, payload_envelope) for ep in targets]
        results = await asyncio.gather(*tasks, return_exceptions=False)
    monitoring.QUEUE_SIZE.labels(queue="webhook").dec()

    logger.info(
        "Event emitted",
        event_type=event_type,
        endpoint_count=len(results),
        successful=sum(1 for r in results if r.get("ok"))
    )
    return results
def register_workflow_endpoint(app: Any, endpoint_id: str, url: str, events: Optional[List[str]] = None) -> Dict[str, Any]:
    """Register a workflow endpoint (idempotent).

    - endpoint_id: unique id for this registration
    - url: webhook URL to POST events to
    - events: list of event types the endpoint wants, or ['*'] for all
    """
    if events is None:
        events = ["*"]
    endpoints: List[Dict[str, Any]] = getattr(app.state, "workflow_endpoints", None)
    if endpoints is None:
        raise OrchestrationError("Orchestration not initialized")

    # replace existing registration if id matches
    for e in endpoints:
        if e.get("id") == endpoint_id:
            e.update({"url": url, "events": events})
            logger.info("Updated workflow endpoint %s", endpoint_id)
            return e

    new = {"id": endpoint_id, "url": url, "events": events}
    endpoints.append(new)
    logger.info("Registered new workflow endpoint %s", endpoint_id)
    return new


def unregister_workflow_endpoint(app: Any, endpoint_id: str) -> bool:
    endpoints: List[Dict[str, Any]] = getattr(app.state, "workflow_endpoints", None) or []
    before = len(endpoints)
    endpoints[:] = [e for e in endpoints if e.get("id") != endpoint_id]
    after = len(endpoints)
    removed = before - after
    logger.info("Unregistered workflow endpoint %s (removed=%d)", endpoint_id, removed)
    return removed > 0
