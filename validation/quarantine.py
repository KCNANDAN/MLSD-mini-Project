import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

QUARANTINE_DIR = Path("storage/quarantine")


def quarantine_petition(
    payload: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    """
    Store an invalid or suspicious petition in quarantine.

    Each quarantined record receives a unique identifier and timestamp.
    """
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

    quarantine_id = str(uuid4())

    record = {
        "quarantine_id": quarantine_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "payload": payload,
        "status": "quarantined",
    }

    file_path = QUARANTINE_DIR / f"{quarantine_id}.json"

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(record, file, indent=2, ensure_ascii=False, default=str)

    return {
        "quarantine_id": quarantine_id,
        "status": "quarantined",
    }