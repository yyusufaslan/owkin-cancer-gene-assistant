"""Structured query/answer logging for model comparison."""
import json
import os
from pathlib import Path
from typing import Any, Optional
import uuid


def get_log_path() -> Path:
    from config.settings import LOG_DIR
    path = Path(LOG_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path / "query_answers.jsonl"


def log_query_answer(
    query: str,
    answer: str,
    model: str,
    request_id: Optional[str] = None,
    tool_calls: Optional[list] = None,
    latency_ms: Optional[float] = None,
) -> str:
    """Append one query/answer record to logs/query_answers.jsonl. Returns request_id."""
    from datetime import datetime
    rid = request_id or str(uuid.uuid4())
    log_path = get_log_path()
    record = {
        "request_id": rid,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "model": model,
        "query": query,
        "answer": answer,
    }
    if tool_calls is not None:
        record["tool_calls"] = tool_calls
    if latency_ms is not None:
        record["latency_ms"] = round(latency_ms, 2)
    with open(log_path, "a") as f:
        f.write(json.dumps(record) + "\n")
    return rid
