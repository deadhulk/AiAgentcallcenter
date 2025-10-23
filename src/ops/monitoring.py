"""Monitoring and observability implementation.

This module provides Prometheus metrics, OpenTelemetry tracing, and structured logging
configuration for the AI call center. It supports both standalone metrics via a
/metrics endpoint and push-based metrics to Prometheus Pushgateway.
"""
from typing import Any, Dict, Optional
import logging
import time
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    CollectorRegistry,
    push_to_gateway,
    generate_latest
)
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
import structlog
import os

# Initialize logging
logger = structlog.get_logger(__name__)

# Prometheus metrics
REGISTRY = CollectorRegistry()

# Counter metrics
CALLS_TOTAL = Counter(
    'calls_total',
    'Total number of calls processed',
    ['status'],
    registry=REGISTRY
)

EVENTS_TOTAL = Counter(
    'events_total',
    'Total number of events processed',
    ['type'],
    registry=REGISTRY
)

ERRORS_TOTAL = Counter(
    'errors_total',
    'Total number of errors encountered',
    ['type'],
    registry=REGISTRY
)

REQUESTS_TOTAL = Counter(
    'requests_total',
    'Total number of API requests processed',
    ['endpoint', 'method', 'status'],
    registry=REGISTRY
)

# Histogram metrics
CALL_DURATION_SECONDS = Histogram(
    'call_duration_seconds',
    'Call duration in seconds',
    buckets=(30, 60, 120, 300, 600, 1800),
    registry=REGISTRY
)

SPEECH_PROCESSING_SECONDS = Histogram(
    'speech_processing_seconds',
    'Speech processing time in seconds',
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0),
    registry=REGISTRY
)

# Gauge metrics
ACTIVE_CALLS = Gauge(
    'active_calls',
    'Number of currently active calls',
    registry=REGISTRY
)

QUEUE_SIZE = Gauge(
    'queue_size',
    'Number of items in processing queue',
    ['queue'],
    registry=REGISTRY
)

def init_monitoring(app: Any):
    """Initialize monitoring for a FastAPI application.
    
    Sets up:
    - Prometheus metrics
    - OpenTelemetry tracing
    - Structured logging
    - Metrics endpoint
    """
    logger.info("Initializing monitoring")
    
    # Initialize OpenTelemetry if configured
    if os.getenv("ENABLE_TRACING", "false").lower() in ("1", "true", "yes"):
        trace.set_tracer_provider(TracerProvider())
        otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://jaeger:4317")
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        span_processor = BatchSpanProcessor(otlp_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        
        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)
    
    # Initialize structured logging
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Store registry in app state for compatibility
    app.state.metrics_registry = REGISTRY
    
    # Initialize legacy metrics dict for backward compatibility
    app.state.metrics = {
        'requests_total': 0,
        'calls_processed': 0,
    }
    
    # Initialize default metrics
    ACTIVE_CALLS.set(0)
    for queue in ["esl", "speech", "crm"]:
        QUEUE_SIZE.labels(queue=queue).set(0)
    
    # Set up Prometheus push gateway if configured
    push_gateway = os.getenv("PROMETHEUS_PUSHGATEWAY")
    if push_gateway:
        app.state.prometheus_push_gateway = push_gateway
        app.state.prometheus_push_job = os.getenv("PROMETHEUS_PUSH_JOB", "ai_callcenter")

def metrics_handler() -> Dict[str, Any]:
    """Return current metrics snapshot as a JSON-friendly dict.
    
    This maintains backward compatibility with the previous metrics format
    while also supporting Prometheus metrics.
    """
    try:
        from fastapi import current_app
        metrics = getattr(current_app.state, 'metrics', None)
        if metrics is None:
            metrics = {'requests_total': 0, 'calls_processed': 0}
        
        # Update legacy metrics from Prometheus counters
        metrics['requests_total'] = sum(REQUESTS_TOTAL._value.values())
        metrics['calls_processed'] = sum(CALLS_TOTAL._value.values())
        return metrics
        
    except Exception:
        logger.debug("metrics_handler fallback, returning default metrics")
        return {'requests_total': 0, 'calls_processed': 0}

def track_request(endpoint: str, method: str, status: int):
    """Track an API request."""
    REQUESTS_TOTAL.labels(endpoint=endpoint, method=method, status=status).inc()

def track_call_start():
    """Track metrics for a new call."""
    CALLS_TOTAL.labels(status="started").inc()
    ACTIVE_CALLS.inc()

def track_call_end(duration_seconds: Optional[float] = None):
    """Track metrics for a completed call."""
    CALLS_TOTAL.labels(status="completed").inc()
    ACTIVE_CALLS.dec()
    if duration_seconds is not None:
        CALL_DURATION_SECONDS.observe(duration_seconds)

def track_error(error_type: str):
    """Track an error occurrence."""
    ERRORS_TOTAL.labels(type=error_type).inc()

def track_event(event_type: str):
    """Track an event occurrence."""
    EVENTS_TOTAL.labels(type=event_type).inc()

def update_queue_size(queue: str, size: int):
    """Update queue size gauge."""
    QUEUE_SIZE.labels(queue=queue).set(size)

def track_speech_processing(duration_seconds: float):
    """Track speech processing duration."""
    SPEECH_PROCESSING_SECONDS.observe(duration_seconds)

async def push_metrics(app: Any):
    """Push metrics to Prometheus Pushgateway if configured."""
    push_gateway = getattr(app.state, "prometheus_push_gateway", None)
    if not push_gateway:
        return
    
    try:
        job = app.state.prometheus_push_job
        push_to_gateway(push_gateway, job, REGISTRY)
    except Exception as e:
        logger.exception("Error pushing metrics", error=str(e))

def get_metrics() -> bytes:
    """Get current metrics in Prometheus format."""
    return generate_latest(REGISTRY)

# Tracing helpers
def start_call_span(call_id: str) -> Any:
    """Start a new trace span for a call."""
    tracer = trace.get_tracer(__name__)
    return tracer.start_as_current_span(
        name="process_call",
        attributes={
            "call.id": call_id
        }
    )

def start_span(name: str) -> Any:
    """Start a new trace span (not as current)."""
    tracer = trace.get_tracer(__name__)
    return tracer.start_span(
        name=name
    )

def start_speech_span(call_id: str) -> Any:
    """Start a new trace span for speech processing."""
    tracer = trace.get_tracer(__name__)
    return tracer.start_span(
        name="speech_processing",
        attributes={
            "call.id": call_id
        }
    )

def record_error(span: Any, error: Exception):
    """Record an error in the current span."""
    if span is not None:
        span.set_status(Status(StatusCode.ERROR))
        span.record_exception(error)
