"""
JSONManager
===========
Handles reading and writing Account records to/from JSON files.
"""

import json
import logging
from pathlib import Path

from src.account_manager import Account

logger = logging.getLogger(__name__)


class JSONManager:
    """Persists Account objects to a JSON file."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    def save(self, accounts: list[Account]) -> None:
        """
        Write all accounts to a JSON file.

        Args:
            accounts: List of Account objects to save.
        """
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        data = [a.to_dict() for a in accounts]
        with self.file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Saved %d accounts to %s", len(accounts), self.file_path)

    def load(self) -> list[Account]:
        """
        Load accounts from a JSON file.

        Returns:
            List of Account objects, or empty list if file doesn't exist.
        """
        if not self.file_path.exists():
            return []

        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                data: list[dict] = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load JSON vault: %s", exc)
            return []

        accounts = []
        for row in data:
            try:
                accounts.append(Account.from_dict(row))
            except Exception as exc:
                logger.warning("Skipping malformed entry: %s", exc)

        logger.info("Loaded %d accounts from %s", len(accounts), self.file_path)
        return accounts
