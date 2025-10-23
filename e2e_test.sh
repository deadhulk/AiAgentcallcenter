#!/bin/bash

# E2E Test Script for AI Agent Call Center

# Function to check if the service is up
check_service() {
    curl -s http://localhost:8000/health || return 1
    return 0
}

# Function to run a test call flow
test_call_flow() {
    # Test 1: Initialize a call
    echo "Testing call initialization..."
    CALL_ID=$(curl -s -X POST "http://localhost:8000/api/calls/init" \
        -H "Content-Type: application/json" \
        -d '{"user_id": "test_user", "phone_number": "+1234567890"}' | jq -r '.call_id')

    if [ -z "$CALL_ID" ]; then
        echo "Failed to initialize call"
        return 1
    fi

    # Test 2: Send audio/text
    echo "Testing audio/text processing..."
    curl -s -X POST "http://localhost:8000/api/calls/$CALL_ID/process" \
        -H "Content-Type: application/json" \
        -d '{"input": "test message"}'

    # Test 3: Check call status
    echo "Checking call status..."
    curl -s "http://localhost:8000/api/calls/$CALL_ID"

    # Test 4: End call
    echo "Ending call..."
    curl -s -X POST "http://localhost:8000/api/calls/$CALL_ID/end"
}

# Main test execution
echo "Starting E2E tests..."

# Wait for service to be up
echo "Waiting for service to be available..."
RETRIES=0
while ! check_service && [ $RETRIES -lt 30 ]; do
    sleep 1
    ((RETRIES++))
done

if [ $RETRIES -eq 30 ]; then
    echo "Service failed to start"
    exit 1
fi

# Run test flow
test_call_flow

echo "E2E tests completed"