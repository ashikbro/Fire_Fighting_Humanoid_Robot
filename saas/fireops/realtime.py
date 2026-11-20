"""In-process pub/sub hub that fans events out to browser WebSockets per organisation."""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict

from fastapi import WebSocket


class Hub:
    def __init__(self) -> None:
        self._clients: dict[int, set[WebSocket]] = defaultdict(set)
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, org_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._clients[org_id].add(ws)

    def disconnect(self, org_id: int, ws: WebSocket) -> None:
        self._clients[org_id].discard(ws)

    def client_count(self, org_id: int) -> int:
        return len(self._clients.get(org_id, ()))

    async def _send_all(self, org_id: int, message: str) -> None:
        dead = []
        for ws in list(self._clients.get(org_id, ())):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(org_id, ws)

    def publish(self, org_id: int, event: str, data: dict) -> None:
        """Thread-safe publish usable from sync request handlers and background threads."""
        if not self._clients.get(org_id) or self._loop is None:
            return
        message = json.dumps({"event": event, "data": data}, default=str)
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is self._loop:
            self._loop.create_task(self._send_all(org_id, message))
        else:
            asyncio.run_coroutine_threadsafe(self._send_all(org_id, message), self._loop)


hub = Hub()
