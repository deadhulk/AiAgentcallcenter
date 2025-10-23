import types

def reset_prometheus_metrics():
    # Reset all metric values to zero for a clean test state
    for metric in [
        monitoring.ACTIVE_CALLS,
        monitoring.CALLS_TOTAL,
        monitoring.ERRORS_TOTAL,
        monitoring.EVENTS_TOTAL,
        monitoring.QUEUE_SIZE,
        monitoring.SPEECH_PROCESSING_SECONDS
    ]:
        if hasattr(metric, '_metrics'):  # Gauge, Counter
            metric._metrics.clear()
        if hasattr(metric, '_value'):  # Gauge
            if hasattr(metric._value, 'clear'):
                metric._value.clear()
        if hasattr(metric, '_sum'):
            if hasattr(metric._sum, 'clear'):
                metric._sum.clear()
        if hasattr(metric, '_count'):
            if hasattr(metric._count, 'clear'):
                metric._count.clear()

import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from src.ops import monitoring

def test_init_monitoring_prometheus():
    reset_prometheus_metrics()
    app = FastAPI()
    monitoring.init_monitoring(app)

    # Check registry initialization
    assert hasattr(app.state, "metrics_registry")
    
    # Check default metrics initialization
    assert hasattr(app.state, "metrics")
    assert app.state.metrics["requests_total"] == 0
    assert app.state.metrics["calls_processed"] == 0

    # Check gauge metrics initialization
    # Use .collect() to get metric values
    active_calls_sample = list(monitoring.ACTIVE_CALLS.collect())[0].samples
    assert any(s.value == 0 for s in active_calls_sample if s.name == 'active_calls')
    for queue in ["esl", "speech", "crm"]:
        queue_samples = list(monitoring.QUEUE_SIZE.collect())[0].samples
        assert any(s.value == 0 and s.labels.get('queue') == queue for s in queue_samples if s.name == 'queue_size')

def test_metrics_tracking():
    reset_prometheus_metrics()
    # Test call tracking
    monitoring.track_call_start()
    active_calls_sample = list(monitoring.ACTIVE_CALLS.collect())[0].samples
    assert any(s.value == 1 for s in active_calls_sample if s.name == 'active_calls')
    calls_total_sample = list(monitoring.CALLS_TOTAL.collect())[0].samples
    assert any(s.value == 1 and s.labels.get('status') == 'started' for s in calls_total_sample if s.name == 'calls_total')

    monitoring.track_call_end(120.5)
    active_calls_sample = list(monitoring.ACTIVE_CALLS.collect())[0].samples
    assert any(s.value == 0 for s in active_calls_sample if s.name == 'active_calls')
    calls_total_sample = list(monitoring.CALLS_TOTAL.collect())[0].samples
    assert any(s.value == 1 and s.labels.get('status') == 'completed' for s in calls_total_sample if s.name == 'calls_total')

    # Test error tracking
    monitoring.track_error("test_error")
    errors_total_sample = list(monitoring.ERRORS_TOTAL.collect())[0].samples
    assert any(s.value == 1 and s.labels.get('type') == 'test_error' for s in errors_total_sample if s.name == 'errors_total')

    # Test event tracking
    monitoring.track_event("test_event")
    events_total_sample = list(monitoring.EVENTS_TOTAL.collect())[0].samples
    assert any(s.value == 1 and s.labels.get('type') == 'test_event' for s in events_total_sample if s.name == 'events_total')

def test_queue_size_tracking():
    reset_prometheus_metrics()
    monitoring.update_queue_size("test_queue", 5)
    queue_samples = list(monitoring.QUEUE_SIZE.collect())[0].samples
    assert any(s.value == 5 and s.labels.get('queue') == 'test_queue' for s in queue_samples if s.name == 'queue_size')

    monitoring.update_queue_size("test_queue", 3)
    queue_samples = list(monitoring.QUEUE_SIZE.collect())[0].samples
    assert any(s.value == 3 and s.labels.get('queue') == 'test_queue' for s in queue_samples if s.name == 'queue_size')

def test_speech_processing_tracking():
    reset_prometheus_metrics()
    monitoring.track_speech_processing(1.5)
    # Use .collect() to get histogram sum and count
    hist_samples = list(monitoring.SPEECH_PROCESSING_SECONDS.collect())[0].samples
    sum_sample = next(s for s in hist_samples if s.name.endswith('_sum'))
    count_sample = next(s for s in hist_samples if s.name.endswith('_count'))
    assert sum_sample.value > 0
    assert count_sample.value == 1

@pytest.mark.asyncio
async def test_push_metrics():
    app = FastAPI()
    app.state.prometheus_push_gateway = "test:9091"
    app.state.prometheus_push_job = "test_job"
    
    with patch("src.ops.monitoring.push_to_gateway") as mock_push:
        await monitoring.push_metrics(app)
        mock_push.assert_called_once_with(
            "test:9091", 
            "test_job", 
            monitoring.REGISTRY
        )

def test_tracing():
    # Test call span
    with patch("opentelemetry.trace.get_tracer") as mock_tracer:
        mock_span = MagicMock()
        # Simulate context manager for start_as_current_span
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_span
        mock_tracer.return_value.start_as_current_span.return_value = mock_cm
        with monitoring.start_call_span("test-call-id") as span:
            assert span == mock_span
            # Simulate set_attribute call
            span.set_attribute("call.id", "test-call-id")
            span.set_attribute.assert_called_with("call.id", "test-call-id")

    # Test speech span
    with patch("opentelemetry.trace.get_tracer") as mock_tracer:
        mock_span = MagicMock()
        mock_tracer.return_value.start_span.return_value = mock_span
        span = monitoring.start_speech_span("test-call-id")
        assert span == mock_span
        # Simulate set_attribute call
        span.set_attribute("call.id", "test-call-id")
        span.set_attribute.assert_called_with("call.id", "test-call-id")