"""
ExpirationManager
=================
Checks password expiration status across all accounts and prints
actionable warnings to the CLI.
"""

import logging

from src.account_manager import Account, AccountManager

logger = logging.getLogger(__name__)


class ExpirationManager:
    """Surfaces expiration warnings and expired credentials."""

    def __init__(self, warn_days: int = 14) -> None:
        """
        Args:
            warn_days: Days before expiry at which to show warnings.
        """
        self.warn_days = warn_days

    def check_all(self, manager: AccountManager) -> dict[str, list[Account]]:
        """
        Scan all accounts and categorise by expiration status.

        Returns:
            Dict with keys:
              'expired'  — passwords already expired
              'expiring' — expiring within warn_days
              'ok'       — no issues
        """
        expired = manager.get_expired()
        expiring = [
            a for a in manager.get_expiring_soon(self.warn_days)
            if not a.is_expired
        ]
        all_ids = {a.id for a in expired} | {a.id for a in expiring}
        ok = [a for a in manager.list_all() if a.id not in all_ids and a.expires_at]

        return {"expired": expired, "expiring": expiring, "ok": ok}

    def print_warnings(self, manager: AccountManager) -> None:
        """Print expiration warnings to stdout."""
        results = self.check_all(manager)

        if results["expired"]:
            print(f"\n{'─'*55}")
            print(f"  EXPIRED PASSWORDS ({len(results['expired'])})")
            print(f"{'─'*55}")
            for a in results["expired"]:
                print(f"  • {a.website:<30} [{a.username}]  expired {a.expires_at[:10]}")

        if results["expiring"]:
            print(f"\n{'─'*55}")
            print(f"  EXPIRING SOON ({len(results['expiring'])})")
            print(f"{'─'*55}")
            for a in results["expiring"]:
                days = a.days_until_expiry()
                day_str = f"{days} day{'s' if days != 1 else ''}"
                print(f"  • {a.website:<30} [{a.username}]  expires in {day_str}")

        if not results["expired"] and not results["expiring"]:
            print("\n  All passwords are current — no expirations due.")
        print()
