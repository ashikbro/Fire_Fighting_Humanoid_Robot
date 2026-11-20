"""Outbound webhooks (HMAC-signed) delivered from a background worker thread."""
from __future__ import annotations

import json
import logging
import queue
import threading
import time
import urllib.request

from .config import settings
from .db import get_conn
from .security import sign_payload

log = logging.getLogger("fireops.webhooks")
_queue: "queue.Queue[tuple[int, str, dict]]" = queue.Queue(maxsize=10_000)
_worker: threading.Thread | None = None


def emit(org_id: int, event: str, data: dict) -> None:
    try:
        _queue.put_nowait((org_id, event, data))
    except queue.Full:
        log.warning("webhook queue full, dropping %s", event)


def deliver(url: str, secret: str, event: str, data: dict) -> str:
    body = json.dumps({"event": event, "data": data, "sent_at": time.time()}, default=str).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "User-Agent": "FireOps-Webhooks/1.0",
        "X-FireOps-Event": event,
        "X-FireOps-Signature": "sha256=" + sign_payload(secret, body),
    })
    try:
        with urllib.request.urlopen(req, timeout=settings.webhook_timeout) as resp:
            return f"{resp.status}"
    except Exception as exc:  # network errors are recorded, never raised
        return f"error: {exc}"[:200]


def _process(org_id: int, event: str, data: dict) -> None:
    with get_conn() as conn:
        hooks = conn.execute("SELECT * FROM webhooks WHERE org_id=? AND enabled=1", (org_id,)).fetchall()
    for h in hooks:
        events = h["events"]
        if events != "*" and event not in [e.strip() for e in events.split(",")]:
            continue
        status = deliver(h["url"], h["secret"], event, data)
        with get_conn() as conn:
            conn.execute("UPDATE webhooks SET last_status=? WHERE id=?", (status, h["id"]))


def _run() -> None:
    while True:
        org_id, event, data = _queue.get()
        try:
            _process(org_id, event, data)
        except Exception:
            log.exception("webhook delivery failed")


def start_worker() -> None:
    global _worker
    if _worker is None or not _worker.is_alive():
        _worker = threading.Thread(target=_run, name="fireops-webhooks", daemon=True)
        _worker.start()
