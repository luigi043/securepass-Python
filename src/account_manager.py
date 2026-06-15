"""
AccountManager
==============
Manages the lifecycle of credential accounts:
create, read, update, delete, search, and password history.

All accounts are stored in-memory as Account dataclass instances
and persisted via CSVManager / JSONManager.
"""

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

CATEGORIES = [
    "Personal", "Work", "Banking", "Social Media",
    "Gaming", "Shopping", "Education", "Other",
]


@dataclass
class Account:
    """Represents a single stored credential."""
    id: str
    username: str
    email: str
    website: str
    password: str                       # Stored in plaintext in vault (encrypted at rest)
    category: str = "Personal"
    notes: str = ""
    created_at: str = ""
    expires_at: str = ""
    password_history: list[str] = field(default_factory=list)  # SHA-256 hashes of past passwords

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now().isoformat(timespec="seconds")

    def to_dict(self) -> dict:
        """Serialize to a flat dict for CSV/JSON export."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "website": self.website,
            "password": self.password,
            "category": self.category,
            "notes": self.notes,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "password_history": "|".join(self.password_history),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Account":
        """Deserialize from a flat dict."""
        history_raw = data.get("password_history", "")
        history = history_raw.split("|") if history_raw else []
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            username=data.get("username", ""),
            email=data.get("email", ""),
            website=data.get("website", ""),
            password=data.get("password", ""),
            category=data.get("category", "Personal"),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
            expires_at=data.get("expires_at", ""),
            password_history=history,
        )

    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        try:
            return datetime.fromisoformat(self.expires_at) < datetime.now()
        except ValueError:
            return False

    def days_until_expiry(self) -> Optional[int]:
        if not self.expires_at:
            return None
        try:
            delta = datetime.fromisoformat(self.expires_at) - datetime.now()
            return delta.days
        except ValueError:
            return None


class AccountManager:
    """
    In-memory store for Account objects with full CRUD operations.
    Supports password history tracking to prevent reuse.
    """

    def __init__(self, max_history: int = 5) -> None:
        """
        Args:
            max_history: Max number of past password hashes to remember per account.
        """
        self._accounts: dict[str, Account] = {}  # id → Account
        self.max_history = max_history

    # ── CRUD ──────────────────────────────────────────────────────────────

    def add(
        self,
        website: str,
        username: str,
        email: str,
        password: str,
        category: str = "Personal",
        notes: str = "",
        expiry_days: int = 90,
    ) -> Account:
        """
        Create and store a new account.

        Args:
            username: Login username.
            email: Associated email address.
            website: Website or service name.
            password: The credential password.
            category: One of the predefined categories.
            notes: Optional freeform notes.
            expiry_days: Days until password expiry (0 = never).

        Returns:
            The newly created Account.
        """
        account = Account(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            website=website,
            password=password,
            category=category,
            notes=notes,
            expires_at=(
                (datetime.now() + timedelta(days=expiry_days)).isoformat(timespec="seconds")
                if expiry_days > 0 else ""
            ),
        )
        account.password_history.append(self._hash(password))
        self._accounts[account.id] = account
        logger.info("Added account: %s (%s)", website, username)
        return account

    def get(self, account_id: str) -> Optional[Account]:
        """Retrieve an account by ID."""
        return self._accounts.get(account_id)

    def update(
        self,
        account_id: str,
        *,
        username: Optional[str] = None,
        email: Optional[str] = None,
        website: Optional[str] = None,
        password: Optional[str] = None,
        category: Optional[str] = None,
        notes: Optional[str] = None,
        expiry_days: Optional[int] = None,
    ) -> Account:
        """
        Update fields on an existing account.

        If a new password is provided, it's checked against history
        and the old one is pushed into the history stack.

        Raises:
            KeyError: If account_id does not exist.
            ValueError: If the new password was used recently.
        """
        account = self._accounts.get(account_id)
        if not account:
            raise KeyError(f"Account not found: {account_id}")

        if username is not None:
            account.username = username
        if email is not None:
            account.email = email
        if website is not None:
            account.website = website
        if category is not None:
            account.category = category
        if notes is not None:
            account.notes = notes

        if password is not None:
            pw_hash = self._hash(password)
            if pw_hash in account.password_history:
                raise ValueError("This password was used recently. Choose a different one.")
            # Push current password to history, trim to max
            account.password_history.append(pw_hash)
            if len(account.password_history) > self.max_history:
                account.password_history = account.password_history[-self.max_history:]
            account.password = password

        if expiry_days is not None:
            account.expires_at = (
                (datetime.now() + timedelta(days=expiry_days)).isoformat(timespec="seconds")
                if expiry_days > 0 else ""
            )

        logger.info("Updated account: %s", account_id)
        return account

    def delete(self, account_id: str) -> None:
        """
        Remove an account.

        Raises:
            KeyError: If account_id does not exist.
        """
        if account_id not in self._accounts:
            raise KeyError(f"Account not found: {account_id}")
        website = self._accounts[account_id].website
        del self._accounts[account_id]
        logger.info("Deleted account: %s (%s)", account_id, website)

    # ── Query ─────────────────────────────────────────────────────────────

    def list_all(self) -> list[Account]:
        """Return all accounts sorted by website."""
        return sorted(self._accounts.values(), key=lambda a: a.website.lower())

    def search(self, query: str) -> list[Account]:
        """
        Search accounts by website, username, or email (case-insensitive).

        Args:
            query: Search term.

        Returns:
            List of matching Account objects.
        """
        q = query.lower()
        return [
            a for a in self._accounts.values()
            if q in a.website.lower()
            or q in a.username.lower()
            or q in a.email.lower()
        ]

    def get_expiring_soon(self, warn_days: int = 14) -> list[Account]:
        """Return accounts whose passwords expire within `warn_days`."""
        results = []
        for account in self._accounts.values():
            days = account.days_until_expiry()
            if days is not None and 0 <= days <= warn_days:
                results.append(account)
        return sorted(results, key=lambda a: a.expires_at)

    def get_expired(self) -> list[Account]:
        """Return all accounts with expired passwords."""
        return [a for a in self._accounts.values() if a.is_expired]

    def load_from_list(self, accounts: list[Account]) -> None:
        """Bulk-load accounts (used when deserializing from CSV/JSON)."""
        self._accounts = {a.id: a for a in accounts}

    # ── Utility ───────────────────────────────────────────────────────────

    @staticmethod
    def _hash(password: str) -> str:
        """SHA-256 hash a password for history comparison."""
        return hashlib.sha256(password.encode()).hexdigest()
