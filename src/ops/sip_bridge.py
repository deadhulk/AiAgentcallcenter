"""Simple FreeSWITCH SIP bridge skeleton.

This module provides a lightweight class that can be extended to connect to
FreeSWITCH via Event Socket Layer (ESL) or REST. For PoC/demo we provide a
non-blocking skeleton that supports start/stop and a small API to map incoming
SIP calls to internal call handlers.

Note: production deployments should use a hardened gateway (Kamailio/OpenSIPS,
or Asterisk/Freeswitch with proper TLS and RTP handling). This module is a
helper for orchestration and integration testing.
"""
from typing import Any, Callable, Optional
import threading
import logging
import os

logger = logging.getLogger(__name__)


class FreeSWITCHBridge:
    def __init__(self, on_call_callback: Optional[Callable[[str, Any], Any]] = None):
        """Create a FreeSWITCHBridge.

        on_call_callback: callable(session_id, call_metadata) invoked when a SIP
        call arrives and should be bridged into the system.
        """
        self.on_call_callback = on_call_callback
        self._running = False
        self._thread = None

    def start(self):
        """Start the bridge (non-blocking)."""
        if self._running:
            return
        self._running = True
        # In a real implementation we'd connect to FreeSWITCH ESL here.
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("FreeSWITCHBridge started (skeleton)")

    def _run(self):
        # Placeholder loop for receiving events from FreeSWITCH.
        import time
        while self._running:
            time.sleep(1)

    def shutdown(self):
        """Stop the bridge and cleanup resources."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        logger.info("FreeSWITCHBridge stopped")

    def simulate_incoming_call(self, session_id: str, metadata: Any = None):
        """Helper for tests: simulate an incoming SIP call arriving from the PSTN."""
        logger.info("Simulating incoming call %s", session_id)
        if callable(self.on_call_callback):
            try:
                self.on_call_callback(session_id, metadata)
            except Exception:
                logger.exception("Error in on_call_callback during simulation")
