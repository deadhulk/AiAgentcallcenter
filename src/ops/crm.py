"""CRM integration adapters for pushing call data to external CRM systems."""
from typing import Dict, Any, Optional
import httpx
import logging
import os
from pydantic import BaseModel, HttpUrl
from datetime import datetime

logger = logging.getLogger(__name__)

class CRMCallData(BaseModel):
    """Schema for call data sent to CRM systems."""
    call_id: str
    customer_id: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    call_type: str = "inbound"
    transcript: Optional[str]
    sentiment_score: Optional[float]
    tags: list[str] = []
    metadata: Dict[str, Any] = {}


class BaseCRMAdapter:
    """Base class for CRM integrations."""

    async def create_contact(self, data: Dict[str, Any]) -> Optional[str]:
        """Create or update a contact in the CRM."""
        raise NotImplementedError()

    async def log_call(self, data: CRMCallData) -> bool:
        """Log a call record in the CRM."""
        raise NotImplementedError()

    async def create_ticket(self, title: str, description: str, priority: str = "normal",
                          metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Create a support ticket in the CRM."""
        raise NotImplementedError()


class WebhookCRMAdapter(BaseCRMAdapter):
    """Generic webhook-based CRM adapter.
    
    This adapter POSTs data to configurable webhook endpoints. Use this as a starting
    point for specific CRM integrations or with webhook-based automation platforms.
    """
    def __init__(self, base_url: str, 
                api_key: Optional[str] = None,
                endpoints: Optional[Dict[str, str]] = None):
        """Initialize webhook CRM adapter.
        
        Args:
            base_url: Base URL for webhook endpoints
            api_key: Optional API key for authentication
            endpoints: Optional mapping of action->endpoint path overrides
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or os.getenv("CRM_API_KEY")
        
        # Default endpoint paths
        self.endpoints = {
            "contact": "/contacts",
            "call": "/calls",
            "ticket": "/tickets"
        }
        if endpoints:
            self.endpoints.update(endpoints)

    async def _post(self, endpoint: str, data: Dict[str, Any]) -> httpx.Response:
        """Send authenticated POST request to webhook endpoint."""
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        async with httpx.AsyncClient() as client:
            return await client.post(url, json=data, headers=headers)

    async def create_contact(self, data: Dict[str, Any]) -> Optional[str]:
        try:
            response = await self._post(self.endpoints["contact"], data)
            response.raise_for_status()
            json_data = await response.json()
            return json_data.get("id")
        except Exception as e:
            logger.exception("Error creating contact")
            return None

    async def log_call(self, data: CRMCallData) -> bool:
        try:
            response = await self._post(self.endpoints["call"], data.dict())
            response.raise_for_status()
            return True
        except Exception as e:
            logger.exception("Error logging call")
            return False

    async def create_ticket(self, title: str, description: str, priority: str = "normal",
                          metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        try:
            data = {
                "title": title,
                "description": description,
                "priority": priority,
                "metadata": metadata or {}
            }
            response = await self._post(self.endpoints["ticket"], data)
            response.raise_for_status()
            json_data = await response.json()
            return json_data.get("id")
        except Exception as e:
            logger.exception("Error creating ticket")
            return None


class SalesforceCRMAdapter(BaseCRMAdapter):
    """Salesforce CRM adapter using the REST API.
    
    This is a placeholder implementation. In production, use the official
    Salesforce SDK and implement proper OAuth2 flow.
    """
    def __init__(self, instance_url: str, access_token: Optional[str] = None):
        self.instance_url = instance_url.rstrip('/')
        self.access_token = access_token or os.getenv("SALESFORCE_ACCESS_TOKEN")
        if not self.access_token:
            raise ValueError("Salesforce access token required")

    async def create_contact(self, data: Dict[str, Any]) -> Optional[str]:
        # TODO: Implement using Salesforce REST API
        logger.warning("Salesforce adapter not fully implemented")
        return None

    async def log_call(self, data: CRMCallData) -> bool:
        # TODO: Implement using Salesforce REST API
        logger.warning("Salesforce adapter not fully implemented")
        return False

    async def create_ticket(self, title: str, description: str, priority: str = "normal",
                          metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        # TODO: Implement using Salesforce REST API
        logger.warning("Salesforce adapter not fully implemented")
        return None


def get_crm_adapter() -> BaseCRMAdapter:
    """Factory to get configured CRM adapter.
    
    Uses environment variables:
    - CRM_PROVIDER: Type of CRM ('webhook' or 'salesforce')
    - CRM_WEBHOOK_URL: Base URL for webhook endpoints
    - CRM_API_KEY: API key for authentication
    - SALESFORCE_INSTANCE_URL: Salesforce instance URL
    - SALESFORCE_ACCESS_TOKEN: Salesforce access token
    """
    provider = os.getenv("CRM_PROVIDER", "webhook").lower()
    
    if provider == "webhook":
        webhook_url = os.getenv("CRM_WEBHOOK_URL")
        if not webhook_url:
            raise ValueError("CRM_WEBHOOK_URL required for webhook adapter")
        return WebhookCRMAdapter(webhook_url)
        
    elif provider == "salesforce":
        instance_url = os.getenv("SALESFORCE_INSTANCE_URL")
        if not instance_url:
            raise ValueError("SALESFORCE_INSTANCE_URL required for Salesforce adapter")
        return SalesforceCRMAdapter(instance_url)
        
    else:
        logger.warning("Unknown CRM provider %s, falling back to webhook", provider)
        webhook_url = os.getenv("CRM_WEBHOOK_URL")
        if not webhook_url:
            raise ValueError("CRM_WEBHOOK_URL required for webhook adapter")
        return WebhookCRMAdapter(webhook_url)