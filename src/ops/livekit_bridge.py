"""LiveKit integration for bridging SIP/FreeSWITCH calls to LiveKit rooms.

This module provides a LiveKitBridge class that manages LiveKit room creation,
participant management, and media relay between FreeSWITCH RTP and WebRTC.
"""
from typing import Optional, Dict, Any
import os
import logging
import httpx
from datetime import datetime, timedelta
import jwt

logger = logging.getLogger(__name__)

class LiveKitBridge:
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, host: Optional[str] = None):
        """Initialize LiveKit bridge with API credentials and host.
        
        Uses environment variables by default:
        - LIVEKIT_API_KEY
        - LIVEKIT_API_SECRET  
        - LIVEKIT_HOST (defaults to http://livekit:7880)
        """
        self.api_key = api_key or os.getenv("LIVEKIT_API_KEY", "devkey")
        self.api_secret = api_secret or os.getenv("LIVEKIT_API_SECRET", "secret")
        self.host = host or os.getenv("LIVEKIT_HOST", "http://livekit:7880")

    def generate_token(self, room: str, identity: str, is_admin: bool = False) -> str:
        """Generate a LiveKit access token with room-specific grants."""
        now = datetime.utcnow()
        exp = now + timedelta(hours=24)

        grants = {
            "video": {"room": room, "roomJoin": True, "canPublish": True, "canSubscribe": True},
            "exp": int(exp.timestamp())
        }

        if is_admin:
            grants["video"]["roomAdmin"] = True
            grants["video"]["roomCreate"] = True

        return jwt.encode(
            payload=grants,
            key=self.api_secret,
            algorithm='HS256',
            headers={"kid": self.api_key}
        )

    async def create_room(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create or get a LiveKit room."""
        url = f"{self.host}/twirp/livekit.RoomService/CreateRoom"
        token = self.generate_token(name, "bridge-admin", is_admin=True)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                json={"name": name, "metadata": metadata},
                headers={"Authorization": f"Bearer {token}"}
            )
            resp.raise_for_status()
            return resp.json()

    async def delete_room(self, name: str) -> None:
        """Delete a LiveKit room when the call ends."""
        url = f"{self.host}/twirp/livekit.RoomService/DeleteRoom"
        token = self.generate_token(name, "bridge-admin", is_admin=True)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                json={"room": name},
                headers={"Authorization": f"Bearer {token}"}
            )
            resp.raise_for_status()

    async def get_room_participants(self, room: str) -> Dict[str, Any]:
        """List participants in a LiveKit room."""
        url = f"{self.host}/twirp/livekit.RoomService/ListParticipants"
        token = self.generate_token(room, "bridge-admin", is_admin=True)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                json={"room": room},
                headers={"Authorization": f"Bearer {token}"}
            )
            resp.raise_for_status()
            return resp.json()