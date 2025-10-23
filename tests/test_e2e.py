import pytest
from fastapi.testclient import TestClient
from main import app
import json
import os
import time

client = TestClient(app)

def test_complete_call_flow():
    """Test a complete call flow from start to end"""
    # 1. Start call
    start_response = client.post("/api/call/start", params={"customer_id": "test_customer"})
    assert start_response.status_code == 200
    session_data = start_response.json()
    assert "session_id" in session_data
    session_id = session_data["session_id"]

    # 2. Process multiple messages
    test_messages = [
        "Hello, I need help with my order",
        "My order number is 12345",
        "Yes, I haven't received it yet",
        "Thank you for your help"
    ]

    for message in test_messages:
        # Create test audio file content
        process_response = client.post(
            f"/api/call/process",
            params={"session_id": session_id},
            files={"audio_file": ("test.wav", message.encode())}
        )
        assert process_response.status_code == 200
        response_data = process_response.json()
        assert "message" in response_data
        assert "status" in response_data
        # Add delay to simulate real conversation
        time.sleep(1)

    # 3. End call
    end_response = client.post(f"/api/call/end", params={"session_id": session_id})
    assert end_response.status_code == 200
    assert end_response.json()["status"] == "success"

def test_error_handling():
    """Test various error scenarios"""
    # Test invalid session ID
    process_response = client.post(
        "/api/call/process",
        params={"session_id": "invalid_session"},
        files={"audio_file": ("test.wav", b"test content")}
    )
    assert process_response.status_code == 404

    # Test missing audio file
    start_response = client.post("/api/call/start", params={"customer_id": "test_customer"})
    session_id = start_response.json()["session_id"]
    process_response = client.post("/api/call/process", params={"session_id": session_id})
    assert process_response.status_code == 422

    # Test concurrent calls
    session_ids = []
    for _ in range(5):  # Test 5 concurrent calls
        response = client.post("/api/call/start", params={"customer_id": f"customer_{_}"})
        assert response.status_code == 200
        session_ids.append(response.json()["session_id"])

    # Process messages for all sessions
    for session_id in session_ids:
        response = client.post(
            f"/api/call/process",
            params={"session_id": session_id},
            files={"audio_file": ("test.wav", b"test message")}
        )
        assert response.status_code == 200

    # End all sessions
    for session_id in session_ids:
        response = client.post(f"/api/call/end", params={"session_id": session_id})
        assert response.status_code == 200

def test_edge_cases():
    """Test edge cases and boundary conditions"""
    # Start a call
    start_response = client.post("/api/call/start", params={"customer_id": "test_customer"})
    session_id = start_response.json()["session_id"]

    # Test empty audio
    process_response = client.post(
        f"/api/call/process",
        params={"session_id": session_id},
        files={"audio_file": ("test.wav", b"")}
    )
    assert process_response.status_code == 422

    # Test very large audio file (1MB of random data)
    large_data = os.urandom(1024 * 1024)  # 1MB of random data
    process_response = client.post(
        f"/api/call/process",
        params={"session_id": session_id},
        files={"audio_file": ("test.wav", large_data)}
    )
    assert process_response.status_code in [413, 422]  # Either too large or invalid format

    # Test special characters in audio content
    special_chars = "!@#$%^&*()\n\t\r\n"
    process_response = client.post(
        f"/api/call/process",
        params={"session_id": session_id},
        files={"audio_file": ("test.wav", special_chars.encode())}
    )
    assert process_response.status_code == 200

    # End the call
    client.post(f"/api/call/end", params={"session_id": session_id})

def test_recovery_scenarios():
    """Test system recovery from various failure scenarios"""
    # 1. Test session recovery after error
    start_response = client.post("/api/call/start", params={"customer_id": "test_customer"})
    session_id = start_response.json()["session_id"]

    # Simulate a failed request
    process_response = client.post(
        f"/api/call/process",
        params={"session_id": session_id},
        files={"audio_file": ("test.wav", os.urandom(1024 * 1024))}  # Should fail
    )
    assert process_response.status_code in [413, 422]

    # Verify session is still valid
    process_response = client.post(
        f"/api/call/process",
        params={"session_id": session_id},
        files={"audio_file": ("test.wav", b"recovery test")}
    )
    assert process_response.status_code == 200

    # 2. Test session cleanup
    # End call and verify session is cleaned up
    client.post(f"/api/call/end", params={"session_id": session_id})
    process_response = client.post(
        f"/api/call/process",
        params={"session_id": session_id},
        files={"audio_file": ("test.wav", b"test after cleanup")}
    )
    assert process_response.status_code == 404  # Session should not exist

if __name__ == "__main__":
    pytest.main([__file__])