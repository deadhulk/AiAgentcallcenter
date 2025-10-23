"""Minimal FreeSWITCH Event Socket Layer (ESL) connector.

This connector runs in a background thread with an asyncio loop. It connects
to FreeSWITCH ESL, authenticates, subscribes to events (plain format), and
dispatches parsed events to a user-provided callback.

This is a PoC implementation sufficient for listening to CHANNEL_CREATE,
CHANNEL_ANSWER, HANGUP and other events and issuing simple API/bgapi commands.
"""
from typing import Any, Callable, Dict, Optional
import threading
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class ESLConnector:
    def __init__(self, host: str = "freeswitch", port: int = 8021, password: str = "ClueCon", on_event: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.host = host
        self.port = port
        self.password = password
        self.on_event = on_event

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._cmd_queue: Optional[asyncio.Queue] = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._thread_main, daemon=True)
        self._thread.start()
        logger.info("ESLConnector thread started")

    def stop(self, timeout: float = 2.0):
        self._stop_event.set()
        if self._loop:
            try:
                # Stop the asyncio loop safely
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                logger.exception("Error stopping ESL asyncio loop")
        if self._thread:
            self._thread.join(timeout=timeout)
        logger.info("ESLConnector stopped")

    def _thread_main(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            self._cmd_queue = asyncio.Queue()
            loop.run_until_complete(self._run())
        except Exception:
            logger.exception("ESL connector thread crashed")
        finally:
            try:
                if self._loop and self._loop.is_running():
                    self._loop.stop()
            except Exception:
                pass

    async def _run(self):
        # reconnect loop
        while not self._stop_event.is_set():
            try:
                logger.info("Connecting to FreeSWITCH ESL at %s:%d", self.host, self.port)
                reader, writer = await asyncio.open_connection(self.host, self.port)

                # auth
                writer.write(f"auth {self.password}\n\n".encode())
                await writer.drain()
                await self._drain_plain_response(reader)

                # subscribe to events (plain)
                writer.write(b"event plain ALL\n\n")
                await writer.drain()

                # create task to process outgoing commands
                sender = asyncio.create_task(self._command_sender(writer))

                # read events loop
                while not self._stop_event.is_set():
                    evt = await self._read_event(reader)
                    if evt is None:
                        break
                    try:
                        if callable(self.on_event):
                            # dispatch in thread-safe way
                            self.on_event(evt)
                    except Exception:
                        logger.exception("Error in on_event handler")

                sender.cancel()
                try:
                    await sender
                except Exception:
                    pass

                writer.close()
                await writer.wait_closed()
            except Exception:
                logger.exception("ESL connection error, retrying in 2s")
                await asyncio.sleep(2)

        logger.info("ESL connector exiting run loop")

    async def _command_sender(self, writer: asyncio.StreamWriter):
        assert self._cmd_queue is not None
        while True:
            cmd = await self._cmd_queue.get()
            if cmd is None:
                break
            try:
                writer.write(f"api {cmd}\n\n".encode())
                await writer.drain()
            except Exception:
                logger.exception("Failed to send command to ESL")

    async def _drain_plain_response(self, reader: asyncio.StreamReader):
        # Read until a blank line followed by anything; simple drain used after auth
        try:
            # read lines until we encounter a blank line
            while True:
                line = await reader.readline()
                if not line:
                    return
                if line in (b"\n", b"\r\n"):
                    return
        except Exception:
            return

    async def _read_event(self, reader: asyncio.StreamReader) -> Optional[Dict[str, Any]]:
        # Read headers
        headers: Dict[str, str] = {}
        try:
            while True:
                line = await reader.readline()
                if not line:
                    return None
                s = line.decode(errors="ignore").strip()
                if s == "":
                    break
                # header: key: value
                if ":" in s:
                    k, v = s.split(":", 1)
                    headers[k.strip()] = v.strip()

            # read body if content-length present
            body = ""
            if "Content-Length" in headers:
                try:
                    n = int(headers.get("Content-Length", "0"))
                    if n > 0:
                        data = await reader.readexactly(n)
                        body = data.decode(errors="ignore")
                except Exception:
                    logger.exception("Error reading event body")

            return {"headers": headers, "body": body}
        except Exception:
            logger.exception("Error reading ESL event")
            return None

    def send_api(self, cmd: str):
        """Queue an API command to be sent to FreeSWITCH (thread-safe)."""
        if self._loop is None or self._cmd_queue is None:
            logger.warning("ESLConnector not ready to send commands")
            return
        try:
            asyncio.run_coroutine_threadsafe(self._cmd_queue.put(cmd), self._loop)
        except Exception:
            logger.exception("Failed to enqueue ESL command")
