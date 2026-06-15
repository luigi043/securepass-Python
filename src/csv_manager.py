"""
CSVManager
==========
Handles reading and writing Account records to/from CSV files.
"""

import csv
import logging
from pathlib import Path

from src.account_manager import Account

logger = logging.getLogger(__name__)

CSV_FIELDS = [
    "id", "username", "email", "website", "password",
    "category", "notes", "created_at", "expires_at", "password_history",
]


class CSVManager:
    """Persists Account objects to a CSV file."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    def save(self, accounts: list[Account]) -> None:
        """
        Write all accounts to the CSV file.

        Args:
            accounts: List of Account objects to save.
        """
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for account in accounts:
                writer.writerow(account.to_dict())
        logger.info("Saved %d accounts to %s", len(accounts), self.file_path)

    def load(self) -> list[Account]:
        """
        Load accounts from the CSV file.

        Returns:
            List of Account objects, or empty list if file doesn't exist.
        """
        if not self.file_path.exists():
            logger.debug("CSV file not found: %s", self.file_path)
            return []

        accounts: list[Account] = []
        with self.file_path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    accounts.append(Account.from_dict(dict(row)))
                except Exception as exc:
                    logger.warning("Skipping malformed row: %s", exc)

        logger.info("Loaded %d accounts from %s", len(accounts), self.file_path)
        return accounts
