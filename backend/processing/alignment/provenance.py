from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_alignment_provenance(path: Path, *, metadata: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "phase": "phase_6",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **metadata,
    }
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
