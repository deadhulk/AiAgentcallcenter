import pytest
from fastapi.testclient import TestClient
from main import app
import uuid
from src.api.models import CallSession, CallResponse
from unittest.mock import patch

client = TestClient(app)

def test_start_call():
    customer_id = "test-customer-123"
    response = client.post("/api/call/start", params={"customer_id": customer_id})
    
    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == customer_id
    assert data["status"] == "active"
    assert "session_id" in data

def test_end_call():
    # First start a call
    start_response = client.post("/api/call/start")
    session_id = start_response.json()["session_id"]
    
    # End the call
    end_response = client.post(f"/api/call/end", params={"session_id": session_id})
    
    assert end_response.status_code == 200
    assert end_response.json()["status"] == "success"

def test_end_nonexistent_call():
    response = client.post("/api/call/end", params={"session_id": str(uuid.uuid4())})
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_process_call():
    # Start a call
    start_response = client.post("/api/call/start")
    session_id = start_response.json()["session_id"]
    
    # Create mock audio file
    mock_audio_data = b"test audio data"
    
    # Process the call with test audio (will trigger fallback response)
    response = client.post(
        "/api/call/process",
        params={"session_id": session_id},
        files={"audio_file": ("test.wav", mock_audio_data)}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["message"] == "I'm sorry, I didn't understand that. Could you please rephrase?"
    assert data["audio_path"] is None


def test_process_call_invalid_session():
    response = client.post(
        "/api/call/process",
        params={"session_id": str(uuid.uuid4())},
        files={"audio_file": ("test.wav", b"test audio data")}
    )
    assert response.status_code == 404