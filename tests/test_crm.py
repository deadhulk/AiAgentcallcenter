"""Tests for CRM integration."""
import pytest
from unittest.mock import Mock, patch
import httpx
from datetime import datetime

from src.ops.crm import (
    BaseCRMAdapter,
    WebhookCRMAdapter,
    SalesforceCRMAdapter,
    CRMCallData,
    get_crm_adapter
)

@pytest.fixture
def webhook_crm():
    return WebhookCRMAdapter("http://test-crm.local", api_key="test-key")

@pytest.fixture
def salesforce_crm():
    return SalesforceCRMAdapter("http://test.salesforce.com", access_token="test-token")

@pytest.fixture
def sample_call_data():
    return CRMCallData(
        call_id="test-123",
        customer_id="customer-456",
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
        duration_seconds=60,
        call_type="inbound",
        transcript="Sample transcript",
        sentiment_score=0.5,
        tags=["test"],
        metadata={"source": "test"}
    )

@pytest.mark.asyncio
async def test_webhook_crm_log_call(webhook_crm, sample_call_data):
    """Test logging call via webhook."""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value.status_code = 200
        result = await webhook_crm.log_call(sample_call_data)
        assert result == True
        
        mock_post.assert_called_once()
        called_url = mock_post.call_args[0][0]
        assert called_url == "http://test-crm.local/calls"

@pytest.mark.asyncio
async def test_webhook_crm_create_contact(webhook_crm):
    """Test creating contact via webhook."""
    contact_data = {
        "name": "Test User",
        "email": "test@example.com"
    }
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"id": "contact-123"}
        
        result = await webhook_crm.create_contact(contact_data)
        assert result == "contact-123"
        
        mock_post.assert_called_once()
        called_url = mock_post.call_args[0][0]
        assert called_url == "http://test-crm.local/contacts"

@pytest.mark.asyncio
async def test_webhook_crm_create_ticket(webhook_crm):
    """Test creating ticket via webhook."""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"id": "ticket-123"}
        
        result = await webhook_crm.create_ticket(
            title="Test Issue",
            description="This is a test ticket",
            priority="high"
        )
        assert result == "ticket-123"
        
        mock_post.assert_called_once()
        called_url = mock_post.call_args[0][0]
        assert called_url == "http://test-crm.local/tickets"

def test_crm_adapter_factory():
    """Test CRM adapter factory with different providers."""
    # Test webhook adapter
    with patch.dict("os.environ", {
        "CRM_PROVIDER": "webhook",
        "CRM_WEBHOOK_URL": "http://test-crm.local"
    }):
        adapter = get_crm_adapter()
        assert isinstance(adapter, WebhookCRMAdapter)
    
    # Test Salesforce adapter
    with patch.dict("os.environ", {
        "CRM_PROVIDER": "salesforce",
        "SALESFORCE_INSTANCE_URL": "http://test.salesforce.com",
        "SALESFORCE_ACCESS_TOKEN": "test-token"
    }):
        adapter = get_crm_adapter()
        assert isinstance(adapter, SalesforceCRMAdapter)

def test_call_data_model():
    """Test CRMCallData validation."""
    # Test required fields
    with pytest.raises(Exception):
        CRMCallData()
    # Test valid data (all required fields)
    data = CRMCallData(
        call_id="test-123",
        customer_id="customer-456",
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
        duration_seconds=60,
        call_type="inbound",
        transcript="Sample transcript",
        sentiment_score=0.5,
        tags=[],
        metadata={}
    )
    assert data.call_id == "test-123"
    assert data.call_type == "inbound"  # default value
    assert data.tags == []  # default empty list

@pytest.mark.asyncio
async def test_crm_error_handling(webhook_crm, sample_call_data):
    """Test error handling in CRM operations."""
    with patch("httpx.AsyncClient.post") as mock_post:
        # Test network error
        mock_post.side_effect = httpx.NetworkError("Connection failed")
        result = await webhook_crm.log_call(sample_call_data)
        assert result == False
        
        # Test HTTP error
        mock_post.side_effect = httpx.HTTPError("Server error")
        result = await webhook_crm.create_ticket(
            title="Test",
            description="Test"
        )
        assert result is None