"""
etl/pipeline/state_manager.py
=============================
State and Watermark Manager for Incremental ETL processing.
Maintains state in JSON to track extraction watermarks across pipeline executions.
Uses atomic writes (write-then-rename) to prevent state file corruption during crashes.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from etl.config.settings import settings
from etl.utils.logging import logger


class StateManager:
    """Manages high-watermark timestamps for incremental ETL runs."""

    def __init__(self, state_file_path: Path | None = None) -> None:
        self.state_file_path = state_file_path or settings.state_file_path
        self._ensure_state_dir()

    def _ensure_state_dir(self) -> None:
        """Ensures the parent directory for state files exists."""
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> dict[str, Any]:
        """Loads state dictionary from disk. Returns empty dict if file doesn't exist."""
        if not self.state_file_path.exists():
            return {}
        try:
            with open(self.state_file_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "Corrupted state file detected. Initializing fresh state.",
                path=str(self.state_file_path),
                error=str(e),
            )
            return {}

    def get_watermark(self, entity_name: str) -> str | None:
        """Retrieves the high-watermark timestamp for a specific entity."""
        state = self.load_state()
        entity_state = state.get(entity_name, {})
        watermark = entity_state.get("last_watermark")
        logger.info(
            "Retrieved watermark for entity",
            entity=entity_name,
            watermark=watermark or "NONE (Full Load Required)",
        )
        return watermark

    def update_watermark(
        self,
        entity_name: str,
        watermark: str,
        records_processed: int,
        status: str = "SUCCESS",
    ) -> None:
        """
        Updates the high-watermark timestamp for an entity atomically.
        Writes to a temporary file first, then renames to avoid partial-write corruptions.
        """
        state = self.load_state()
        state[entity_name] = {
            "last_watermark": watermark,
            "last_run_timestamp": datetime.now().isoformat(),
            "records_processed": records_processed,
            "status": status,
        }

        temp_path = self.state_file_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            # Atomic rename (POSIX & Windows compatible in modern Python)
            os.replace(temp_path, self.state_file_path)
            logger.info(
                "Successfully persisted watermark",
                entity=entity_name,
                watermark=watermark,
                records=records_processed,
            )
        except OSError as e:
            logger.error(
                "Failed to write state file atomically",
                path=str(self.state_file_path),
                error=str(e),
            )
            if temp_path.exists():
                temp_path.unlink()
            raise


# Singleton instance
state_manager = StateManager()
