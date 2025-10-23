import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_start_and_end_call():
    # Start a call
    response = client.post("/api/call/start", params={"customer_id": "customer_001"})
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    # End the call
    response = client.post("/api/call/end", params={"session_id": session_id})
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_process_call_with_order():
    # Start a call
    response = client.post("/api/call/start", params={"customer_id": "customer_001"})
    session_id = response.json()["session_id"]
    # Simulate audio containing the word 'order'
    response = client.post(
        "/api/call/process",
        params={"session_id": session_id},
        files={"audio_file": ("dummy.wav", b"order", "audio/wav")}
    )
    assert response.status_code == 200
    assert "order" in response.json()["message"].lower()
    # End the call
    client.post("/api/call/end", params={"session_id": session_id})

def test_process_call_with_working_hours():
    response = client.post("/api/call/start", params={"customer_id": "customer_002"})
    session_id = response.json()["session_id"]
    response = client.post(
        "/api/call/process",
        params={"session_id": session_id},
        files={"audio_file": ("dummy.wav", b"working hours", "audio/wav")}
    )
    assert response.status_code == 200
    assert "working hours" in response.json()["message"].lower()
    client.post("/api/call/end", params={"session_id": session_id})

def test_process_call_with_unknown():
    response = client.post("/api/call/start", params={"customer_id": "customer_003"})
    session_id = response.json()["session_id"]
    response = client.post(
        "/api/call/process",
        params={"session_id": session_id},
        files={"audio_file": ("dummy.wav", b"foobar", "audio/wav")}
    )
    assert response.status_code == 200
    assert "sorry" in response.json()["message"].lower()
    client.post("/api/call/end", params={"session_id": session_id})
