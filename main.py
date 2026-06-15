"""
SecurePass Manager — CLI Entry Point
=====================================
All user interaction flows through this file.
Commands are grouped into subcommands via argparse.
"""

import argparse
import sys
import logging
from pathlib import Path

# ── Bootstrap logging before importing application modules ────────────────
logging.basicConfig(
    filename="logs/app.log",
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
Path("logs").mkdir(exist_ok=True)

from src.vault_service import VaultService  # noqa: E402


BANNER = """
╔══════════════════════════════════════════════╗
║   SecurePass Manager                         ║
║   Credential Vault System  v1.0              ║
╚══════════════════════════════════════════════╝
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="securepass",
        description="SecurePass Manager — Credential Vault System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py generate --length 24
  python main.py generate --passphrase
  python main.py add github.com --username jdoe --email j@example.com
  python main.py list
  python main.py search github
  python main.py check MyP@ssw0rd
  python main.py report
  python main.py expiry
  python main.py vault encrypt
  python main.py vault decrypt
        """,
    )
    sub = parser.add_subparsers(dest="command", metavar="command")

    # ── generate ──────────────────────────────────────────────────────────
    gen = sub.add_parser("generate", help="Generate a secure password")
    gen.add_argument("--length", "-l", type=int, default=None, help="Password length")
    gen.add_argument("--no-upper",   action="store_true", help="Exclude uppercase letters")
    gen.add_argument("--no-lower",   action="store_true", help="Exclude lowercase letters")
    gen.add_argument("--no-digits",  action="store_true", help="Exclude digits")
    gen.add_argument("--no-symbols", action="store_true", help="Exclude symbols")
    gen.add_argument("--passphrase", action="store_true", help="Generate a word-based passphrase")
    gen.add_argument("--count", "-n", type=int, default=1, help="Number of passwords to generate")
    gen.add_argument("--save", metavar="WEBSITE", help="Save generated password for a website")

    # ── check ─────────────────────────────────────────────────────────────
    chk = sub.add_parser("check", help="Check password strength")
    chk.add_argument("password", help="Password to evaluate")

    # ── add ───────────────────────────────────────────────────────────────
    add = sub.add_parser("add", help="Add a new account")
    add.add_argument("website",   help="Website or service name")
    add.add_argument("--username", "-u", required=True, help="Username")
    add.add_argument("--email",    "-e", default="", help="Email address")
    add.add_argument("--password", "-p", default=None, help="Password (auto-generated if omitted)")
    add.add_argument("--category", "-c", default="Personal", help="Category")
    add.add_argument("--notes",    "-n", default="", help="Notes")
    add.add_argument("--expiry",   type=int, default=90, help="Days until expiry (0 = never)")

    # ── list ──────────────────────────────────────────────────────────────
    sub.add_parser("list", help="List all accounts")

    # ── search ────────────────────────────────────────────────────────────
    srch = sub.add_parser("search", help="Search accounts")
    srch.add_argument("query", help="Search term (website / username / email)")

    # ── delete ────────────────────────────────────────────────────────────
    dlt = sub.add_parser("delete", help="Delete an account by ID")
    dlt.add_argument("id", help="Account ID to delete")

    # ── expiry ────────────────────────────────────────────────────────────
    sub.add_parser("expiry", help="Show expiring/expired passwords")

    # ── report ────────────────────────────────────────────────────────────
    sub.add_parser("report", help="Generate full security report")

    # ── vault ─────────────────────────────────────────────────────────────
    vault = sub.add_parser("vault", help="Encrypt or decrypt the vault")
    vault.add_argument("action", choices=["encrypt", "decrypt", "init"], help="Vault action")

    return parser


# ── Command handlers ──────────────────────────────────────────────────────

def cmd_generate(vault: VaultService, args: argparse.Namespace) -> None:
    passwords = [
        vault.generate_password(
            length=args.length,
            uppercase=not args.no_upper,
            lowercase=not args.no_lower,
            digits=not args.no_digits,
            symbols=not args.no_symbols,
            passphrase=args.passphrase,
        )
        for _ in range(args.count)
    ]

    print(f"\n  {'Passphrase' if args.passphrase else 'Password'} Generated")
    print(f"  {'─'*45}")
    for pw in passwords:
        result = vault.strength.analyze(pw)
        print(f"  {pw}")
        print(f"  Strength: {result.label}  ({result.score}/100)")
        if args.count == 1:
            print(f"  Length  : {len(pw)} characters")
    print()

    # Optionally save the first generated password
    if args.save and passwords:
        print(f"  [!] To save, use: python main.py add {args.save} --username <user> --password <above>")


def cmd_check(vault: VaultService, args: argparse.Namespace) -> None:
    result = vault.strength.analyze(args.password)
    print(f"\n  Password Strength Analysis")
    print(f"  {'─'*45}")
    print(f"  Password : {'*' * len(args.password)}")
    print(f"  Score    : {result.score}/100")
    print(f"  Rating   : {result.label}")
    print(f"\n  Feedback:")
    for tip in result.feedback:
        print(f"    • {tip}")
    print()


def cmd_add(vault: VaultService, args: argparse.Namespace) -> None:
    password = args.password or vault.generate_password()
    result = vault.strength.analyze(password)

    account = vault.accounts.add(
        username=args.username,
        email=args.email,
        website=args.website,
        password=password,
        category=args.category,
        notes=args.notes,
        expiry_days=args.expiry,
    )
    vault.save()

    print(f"\n  Account added successfully")
    print(f"  {'─'*45}")
    print(f"  ID       : {account.id[:8]}…")
    print(f"  Website  : {account.website}")
    print(f"  Username : {account.username}")
    print(f"  Password : {password}")
    print(f"  Strength : {result.label}  ({result.score}/100)")
    print(f"  Expires  : {account.expires_at[:10] if account.expires_at else 'Never'}")
    print()


def cmd_list(vault: VaultService) -> None:
    accounts = vault.accounts.list_all()
    if not accounts:
        print("\n  No accounts found. Add one with: python main.py add <website>\n")
        return

    print(f"\n  {'─'*65}")
    print(f"  {'#':<4} {'Website':<22} {'Username':<18} {'Category':<14} {'Expires'}")
    print(f"  {'─'*65}")
    for i, a in enumerate(accounts, 1):
        days = a.days_until_expiry()
        expiry = a.expires_at[:10] if a.expires_at else "Never"
        flag = " [!]" if days is not None and days <= 14 else ""
        flag = " [EXPIRED]" if a.is_expired else flag
        print(f"  {i:<4} {a.website:<22} {a.username:<18} {a.category:<14} {expiry}{flag}")
    print(f"  {'─'*65}")
    print(f"  Total: {len(accounts)} account(s)\n")


def cmd_search(vault: VaultService, args: argparse.Namespace) -> None:
    results = vault.accounts.search(args.query)
    if not results:
        print(f"\n  No accounts found matching '{args.query}'.\n")
        return

    print(f"\n  Search results for '{args.query}' ({len(results)} found)")
    print(f"  {'─'*55}")
    for a in results:
        strength = vault.strength.analyze(a.password)
        print(f"  {a.website}")
        print(f"     ID       : {a.id[:8]}…")
        print(f"     Username : {a.username}")
        print(f"     Email    : {a.email or '—'}")
        print(f"     Category : {a.category}")
        print(f"     Password : {a.password}")
        print(f"     Strength : {strength.label}")
        print(f"     Expires  : {a.expires_at[:10] if a.expires_at else 'Never'}")
        if a.notes:
            print(f"     Notes    : {a.notes}")
        print()


def cmd_delete(vault: VaultService, args: argparse.Namespace) -> None:
    # Support short ID prefix
    all_accounts = vault.accounts.list_all()
    matches = [a for a in all_accounts if a.id.startswith(args.id)]

    if not matches:
        print(f"\n  [ERROR] No account found with ID starting with '{args.id}'\n")
        return
    if len(matches) > 1:
        print(f"\n  [ERROR] Ambiguous ID prefix — {len(matches)} matches. Use more characters.\n")
        return

    account = matches[0]
    vault.accounts.delete(account.id)
    vault.save()
    print(f"\n  Deleted account: {account.website} ({account.username})\n")


def cmd_expiry(vault: VaultService) -> None:
    print(f"\n  Password Expiration Status")
    vault.expiration.print_warnings(vault.accounts)


def cmd_report(vault: VaultService) -> None:
    print()
    vault.reporter.generate(vault.accounts, print_to_console=True)
    print(f"\n  Report saved to: {vault.reporter.output_path}\n")


def cmd_vault(vault: VaultService, args: argparse.Namespace) -> None:
    if args.action == "encrypt":
        vault.encrypt_vault()
    elif args.action == "decrypt":
        vault.decrypt_vault()
    elif args.action == "init":
        vault.encryption.generate_key()
        print(f"  New vault key generated: {vault.encryption.key_path}")
        print("  Keep this file secure. Losing it means losing vault access.")


# ── Entry point ───────────────────────────────────────────────────────────

def main() -> int:
    print(BANNER)
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    try:
        vault = VaultService()
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}")
        return 1

    dispatch = {
        "generate": lambda: cmd_generate(vault, args),
        "check":    lambda: cmd_check(vault, args),
        "add":      lambda: cmd_add(vault, args),
        "list":     lambda: cmd_list(vault),
        "search":   lambda: cmd_search(vault, args),
        "delete":   lambda: cmd_delete(vault, args),
        "expiry":   lambda: cmd_expiry(vault),
        "report":   lambda: cmd_report(vault),
        "vault":    lambda: cmd_vault(vault, args),
    }

    handler = dispatch.get(args.command)
    if handler:
        handler()

    return 0


if __name__ == "__main__":
    sys.exit(main())
