"""Persistent application state for checkpoint and proposal tracking."""

import json
import threading
from pathlib import Path
from typing import Dict, Optional


class AppState:
    """Thread-safe persistent state for last_request_id and proposal map."""

    def __init__(self, state_file: Path = Path("./della_state.json")) -> None:
        """Initialize state.

        Args:
            state_file: Path to JSON state file on disk.
        """
        self._lock = threading.RLock()
        self._state_file = state_file
        self._last_request_id: str = ""
        self._proposal_map: Dict[str, int] = {}  # della_id -> lardi_id

    def load(self) -> None:
        """Load state from disk. Silently ignores missing or corrupt files."""
        try:
            if not self._state_file.exists():
                return
            raw = self._state_file.read_text(encoding="utf-8")
            data = json.loads(raw)
            with self._lock:
                self._last_request_id = data.get("last_request_id", "")
                self._proposal_map = {
                    str(k): int(v)
                    for k, v in data.get("proposal_map", {}).items()
                }
        except Exception:
            pass

    def save(self) -> None:
        """Save current state to disk atomically via a temp file swap."""
        with self._lock:
            data = {
                "last_request_id": self._last_request_id,
                "proposal_map": dict(self._proposal_map),
            }
        try:
            tmp = self._state_file.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(self._state_file)
        except Exception:
            pass

    @property
    def last_request_id(self) -> str:
        """Current checkpoint ID."""
        with self._lock:
            return self._last_request_id

    @last_request_id.setter
    def last_request_id(self, value: str) -> None:
        with self._lock:
            self._last_request_id = value

    def add_proposal(self, della_id: str, lardi_id: int) -> None:
        """Record a published proposal mapping."""
        with self._lock:
            self._proposal_map[della_id] = lardi_id

    def remove_proposal(self, della_id: str) -> None:
        """Remove a proposal from the mapping after deletion."""
        with self._lock:
            self._proposal_map.pop(della_id, None)

    def get_lardi_id(self, della_id: str) -> Optional[int]:
        """Look up the lardi proposal ID for a given della card ID."""
        with self._lock:
            return self._proposal_map.get(della_id)

    @property
    def proposal_count(self) -> int:
        """Number of tracked proposals."""
        with self._lock:
            return len(self._proposal_map)
