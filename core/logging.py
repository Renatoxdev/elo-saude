import json
import logging
import traceback
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path

request_context = ContextVar("request_context", default=None)
EVENTS = {"request_completed", "api_error", "address_provider_failure"}


class SafeJSONFormatter(logging.Formatter):
    """Registra apenas campos permitidos; mensagens e argumentos nunca são serializados."""

    def format(self, record):
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", None)
            if getattr(record, "event", None) in EVENTS
            else "library_event",
        }
        context = request_context.get()
        if context:
            payload.update(context)
        for field in ("status_code", "duration_ms"):
            value = getattr(record, field, None)
            if isinstance(value, (int, float)):
                payload[field] = value
        if record.exc_info and record.exc_info[0]:
            payload["exception_type"] = record.exc_info[0].__name__
            payload["frames"] = [
                {"file": Path(frame.filename).name, "line": frame.lineno, "function": frame.name}
                for frame in traceback.extract_tb(record.exc_info[2])[-8:]
            ]
        return json.dumps(payload, ensure_ascii=False)
