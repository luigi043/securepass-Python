"""
ReportGenerator
===============
Generates a human-readable security audit report covering:
- Total accounts
- Strength distribution
- Expired / expiring passwords
- Category breakdown
- Recommendations
"""

import logging
from collections import Counter
from datetime import datetime
from pathlib import Path

from src.account_manager import Account, AccountManager
from src.password_strength import PasswordStrengthChecker

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Builds and exports security reports for the vault."""

    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        self._checker = PasswordStrengthChecker()

    def generate(self, manager: AccountManager, print_to_console: bool = True) -> str:
        """
        Generate a full security report.

        Args:
            manager: AccountManager with loaded accounts.
            print_to_console: If True, print the report to stdout.

        Returns:
            Report as a string.
        """
        accounts = manager.list_all()
        total = len(accounts)

        if total == 0:
            report = "No accounts found in vault."
            if print_to_console:
                print(report)
            return report

        # Analyse password strengths
        strength_counts: Counter = Counter()
        weak_accounts: list[Account] = []
        scores: list[int] = []

        for account in accounts:
            result = self._checker.analyze(account.password)
            strength_counts[result.label] += 1
            scores.append(result.score)
            if result.score < 60:
                weak_accounts.append(account)

        avg_score = sum(scores) / len(scores) if scores else 0
        expired = manager.get_expired()
        expiring = manager.get_expiring_soon(14)
        categories = Counter(a.category for a in accounts)

        lines = [
            "=" * 57,
            "  SecurePass Manager — Security Report",
            f"  Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 57,
            "",
            "── VAULT SUMMARY ─────────────────────────────────────",
            f"  Total accounts     : {total}",
            f"  Average strength   : {avg_score:.1f}/100",
            f"  Weak passwords     : {len(weak_accounts)}",
            f"  Expired passwords  : {len(expired)}",
            f"  Expiring soon (14d): {len([a for a in expiring if not a.is_expired])}",
            "",
            "── STRENGTH DISTRIBUTION ─────────────────────────────",
        ]
        for label in ["Very Strong", "Strong", "Fair", "Weak", "Very Weak"]:
            count = strength_counts.get(label, 0)
            bar = "█" * count + "░" * max(0, 10 - count)
            lines.append(f"  {label:<12}  {bar}  {count}")

        lines += [
            "",
            "── CATEGORY BREAKDOWN ────────────────────────────────",
        ]
        for cat, count in categories.most_common():
            lines.append(f"  {cat:<20} {count} account{'s' if count != 1 else ''}")

        if weak_accounts:
            lines += [
                "",
                "── WEAK PASSWORDS (action required) ──────────────────",
            ]
            for a in weak_accounts[:10]:
                result = self._checker.analyze(a.password)
                lines.append(f"  • {a.website:<28} score: {result.score}/100  [{result.label}]")
            if len(weak_accounts) > 10:
                lines.append(f"  ... and {len(weak_accounts) - 10} more.")

        if expired:
            lines += [
                "",
                "── EXPIRED PASSWORDS ─────────────────────────────────",
            ]
            for a in expired[:10]:
                lines.append(f"  • {a.website:<28} expired: {a.expires_at[:10]}")

        lines += [
            "",
            "── RECOMMENDATIONS ───────────────────────────────────",
        ]
        if weak_accounts:
            lines.append(f"  Update {len(weak_accounts)} weak password(s) immediately.")
        if expired:
            lines.append(f"  Rotate {len(expired)} expired password(s).")
        if avg_score >= 80:
            lines.append("  Vault health is excellent. Keep it up!")
        elif avg_score >= 60:
            lines.append("  Vault health is acceptable. Consider strengthening weak entries.")
        else:
            lines.append("  Vault health is poor. Prioritise updating weak passwords.")
        lines += ["", "=" * 57]

        report = "\n".join(lines)

        if print_to_console:
            print(report)

        # Save to file
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(report, encoding="utf-8")
        logger.info("Security report saved to %s", self.output_path)

        return report
