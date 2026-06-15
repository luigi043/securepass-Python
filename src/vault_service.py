"""
VaultService
============
Top-level orchestrator. Wires all components together and
provides a clean API used by main.py CLI commands.
"""

import json
import logging
from pathlib import Path

from src.account_manager import AccountManager
from src.csv_manager import CSVManager
from src.encryption_service import EncryptionService
from src.expiration_manager import ExpirationManager
from src.json_manager import JSONManager
from src.password_generator import GeneratorOptions, PasswordGenerator
from src.password_strength import PasswordStrengthChecker
from src.report_generator import ReportGenerator

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path("config/config.json")


class VaultService:
    """
    Coordinates all SecurePass subsystems.
    Instantiated once at startup by main.py.
    """

    def __init__(self, config_path: Path = DEFAULT_CONFIG) -> None:
        cfg = self._load_config(config_path)

        vcfg = cfg["vault"]
        self._csv_path        = Path(vcfg["csv_path"])
        self._json_path       = Path(vcfg["json_path"])
        self._encrypted_path  = Path(vcfg["encrypted_path"])
        self._key_path        = Path(vcfg["key_path"])
        self._warn_days       = cfg["expiration"]["warn_days_before"]
        self._default_expiry  = cfg["expiration"]["default_days"]
        self._max_history     = cfg["history"]["max_entries"]
        self._report_path     = Path(cfg["report"]["output_path"])
        self._pw_cfg          = cfg["password"]

        # Initialise subsystems
        self.accounts    = AccountManager(max_history=self._max_history)
        self.csv         = CSVManager(self._csv_path)
        self.json_mgr    = JSONManager(self._json_path)
        self.encryption  = EncryptionService(self._key_path)
        self.generator   = PasswordGenerator()
        self.strength    = PasswordStrengthChecker()
        self.expiration  = ExpirationManager(warn_days=self._warn_days)
        self.reporter    = ReportGenerator(self._report_path)

        # Load existing accounts from CSV if present
        self._load_vault()

    # ── Vault persistence ─────────────────────────────────────────────────

    def save(self) -> None:
        """Persist current accounts to CSV and JSON."""
        all_accounts = self.accounts.list_all()
        self.csv.save(all_accounts)
        self.json_mgr.save(all_accounts)
        logger.info("Vault saved (%d accounts).", len(all_accounts))

    def encrypt_vault(self) -> None:
        """Encrypt the CSV vault to encrypted_vault.dat."""
        self.save()
        self.encryption.ensure_key()
        self.encryption.encrypt_file(self._csv_path, self._encrypted_path)
        print(f"  Vault encrypted → {self._encrypted_path}")

    def decrypt_vault(self) -> None:
        """Decrypt the vault and reload accounts."""
        self.encryption.load_key()
        self.encryption.decrypt_file(self._encrypted_path, self._csv_path)
        self._load_vault()
        print(f"  Vault decrypted → {self._csv_path}")

    # ── Password generation ───────────────────────────────────────────────

    def generate_password(
        self,
        length: int | None = None,
        uppercase: bool = True,
        lowercase: bool = True,
        digits: bool = True,
        symbols: bool = True,
        passphrase: bool = False,
    ) -> str:
        if passphrase:
            return self.generator.generate_passphrase()

        opts = GeneratorOptions(
            length=length or self._pw_cfg["default_length"],
            uppercase=uppercase,
            lowercase=lowercase,
            digits=digits,
            symbols=symbols,
        )
        return self.generator.generate(opts)

    # ── Private ───────────────────────────────────────────────────────────

    def _load_vault(self) -> None:
        accounts = self.csv.load()
        self.accounts.load_from_list(accounts)
        if accounts:
            logger.info("Loaded %d accounts from vault.", len(accounts))

    @staticmethod
    def _load_config(path: Path) -> dict:
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
