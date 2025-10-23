import pytest
from unittest.mock import MagicMock, patch
from src.ops import orchestration

class DummyApp:
    class State:
        pass
    state = State()

def test_init_orchestration_basic():
    app = DummyApp()
    with patch('src.ops.orchestration.get_crm_adapter', return_value=MagicMock()):
        orchestration.init_orchestration(app)
    assert hasattr(app.state, 'workflow_endpoints')
    assert isinstance(app.state.workflow_endpoints, list)
    assert hasattr(app.state, 'crm_adapter')
    assert hasattr(app.state, 'active_calls')
    assert hasattr(app.state, 'event_loop')
    assert hasattr(app.state, 'sip_bridge')

def test_register_and_unregister_workflow_endpoint():
    app = DummyApp()
    app.state.workflow_endpoints = []
    orchestration.register_workflow_endpoint(app, 'test1', 'http://example.com', ['call.created'])
    assert len(app.state.workflow_endpoints) == 1
    orchestration.unregister_workflow_endpoint(app, 'test1')
    assert len(app.state.workflow_endpoints) == 0

def test_shutdown_orchestration_handles_exceptions():
    app = DummyApp()
    app.state.sip_bridge = MagicMock()
    app.state.sip_bridge.shutdown.side_effect = Exception('fail')
    app.state.crm_adapter = None
    app.state.active_calls = {}
    # Should not raise
    orchestration.shutdown_orchestration(app)

import asyncio

@pytest.mark.asyncio
async def test_emit_event_no_endpoints():
    app = DummyApp()
    app.state.workflow_endpoints = []
    app.state.crm_adapter = None
    app.state.active_calls = {}
    results = await orchestration.emit_event(app, 'call.created', {'uuid': '123'})
    assert results == []
