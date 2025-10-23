"""Extended FreeSWITCH ESL connector with WebRTC bridge support.

This module extends the base ESLConnector with methods specific to bridging
SIP/RTP calls to LiveKit WebRTC rooms via mod_verto.
"""
from typing import Any, Callable, Dict, Optional
from .esl_connector import ESLConnector
from .livekit_bridge import LiveKitBridge
import asyncio
import logging
import json
import os

logger = logging.getLogger(__name__)

class SIPBridgeConnector(ESLConnector):
    """Extended ESLConnector that manages SIP <-> LiveKit bridging."""

    def __init__(self, host: str = "freeswitch", port: int = 8021, password: str = "ClueCon", 
                on_event: Optional[Callable[[Dict[str, Any]], None]] = None):
        super().__init__(host=host, port=port, password=password, on_event=self._on_event_wrapper)
        self._user_event_handler = on_event
        self.livekit = LiveKitBridge()
        # track active bridges
        self._bridges: Dict[str, Dict[str, Any]] = {}

    def _on_event_wrapper(self, evt: Dict[str, Any]):
        """Intercept events for bridge management then forward to user handler."""
        try:
            headers = evt.get("headers", {})
            event_name = headers.get("Event-Name", "")
            
            if event_name == "CHANNEL_CREATE":
                # New inbound call
                uuid = headers.get("Unique-ID")
                if uuid:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self._handle_new_call(uuid, headers))
            
            elif event_name == "CHANNEL_ANSWER":
                uuid = headers.get("Unique-ID")
                if uuid and uuid in self._bridges:
                    # Call was answered, establish WebRTC bridge
                    loop = asyncio.get_event_loop()
                    loop.create_task(self._establish_bridge(uuid))
            
            elif event_name == "CHANNEL_HANGUP":
                uuid = headers.get("Unique-ID")
                if uuid in self._bridges:
                    # Clean up LiveKit room
                    loop = asyncio.get_event_loop() 
                    loop.create_task(self._cleanup_bridge(uuid))
            
            # Forward to user's event handler
            if self._user_event_handler:
                self._user_event_handler(evt)
        
        except Exception:
            logger.exception("Error in bridge event handler")

    async def _handle_new_call(self, uuid: str, headers: Dict[str, str]):
        """Set up LiveKit room for new incoming call."""
        try:
            caller = headers.get("Caller-Caller-ID-Number", "unknown")
            room_name = f"call-{uuid}"
            
            # Create LiveKit room 
            room = await self.livekit.create_room(
                room_name,
                metadata={
                    "caller": caller,
                    "uuid": uuid,
                    "type": "sip-bridge"
                }
            )

            # Track the bridge
            self._bridges[uuid] = {
                "room": room_name,
                "caller": caller,
                "start_time": asyncio.get_event_loop().time()
            }

            logger.info("Created LiveKit room %s for call %s", room_name, uuid)

        except Exception:
            logger.exception("Error setting up bridge for new call")

    async def _establish_bridge(self, uuid: str):
        """Set up WebRTC bridge for answered call."""
        try:
            if uuid not in self._bridges:
                logger.error("Cannot establish bridge - call %s not tracked", uuid)
                return
                
            bridge = self._bridges[uuid]
            room = bridge["room"]
            
            # Generate token for bridge user
            token = self.livekit.generate_token(room, f"sip-{uuid}", is_admin=True)
            
            # Set up WebRTC endpoint via ESL
            # Note: This assumes FreeSWITCH is compiled with mod_verto for WebRTC
            self.send_api(f'uuid_setvar {uuid} webrtc_token {token}')
            self.send_api(f'uuid_setvar {uuid} webrtc_room {room}')
            self.send_api(f'uuid_bridge {uuid} verto/bridge')
            
            logger.info("Established WebRTC bridge for call %s to room %s", uuid, room)

        except Exception:
            logger.exception("Error establishing WebRTC bridge")

    async def _cleanup_bridge(self, uuid: str):
        """Clean up when call ends."""
        try:
            if uuid not in self._bridges:
                return
            
            bridge = self._bridges[uuid]
            room = bridge["room"]
            
            # Remove from tracking
            del self._bridges[uuid]
            
            # Delete LiveKit room
            try:
                await self.livekit.delete_room(room)
                logger.info("Cleaned up LiveKit room %s for ended call %s", room, uuid)
            except Exception:
                logger.exception("Error cleaning up LiveKit room %s", room)

        except Exception:
            logger.exception("Error cleaning up bridge")