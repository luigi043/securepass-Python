"""
EncryptionService
=================
Encrypts and decrypts files using Fernet symmetric encryption
from the `cryptography` library.

Fernet guarantees:
- AES-128-CBC encryption
- HMAC-SHA256 authentication
- Timestamp-based token validation

The encryption key is generated once and stored in vault/.vault.key
This file must be kept secret — it is the master key to the vault.
"""

import logging
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Symmetric file encryption/decryption using Fernet.

    Usage:
        svc = EncryptionService(key_path=Path("vault/.vault.key"))
        svc.encrypt_file(Path("vault/accounts.csv"), Path("vault/encrypted_vault.dat"))
        svc.decrypt_file(Path("vault/encrypted_vault.dat"), Path("vault/accounts_restored.csv"))
    """

    def __init__(self, key_path: Path) -> None:
        """
        Args:
            key_path: Path where the Fernet key is stored (or will be created).
        """
        self.key_path = key_path
        self._fernet: Fernet | None = None

    # ── Key management ────────────────────────────────────────────────────

    def generate_key(self) -> None:
        """
        Generate a new Fernet key and save it to disk.

        Warning: Generating a new key invalidates any previously encrypted vault.
        """
        key = Fernet.generate_key()
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        self.key_path.write_bytes(key)
        # Restrict file permissions on Unix systems
        try:
            self.key_path.chmod(0o600)
        except NotImplementedError:
            pass  # Windows doesn't support chmod
        self._fernet = Fernet(key)
        logger.info("Generated new encryption key: %s", self.key_path)

    def load_key(self) -> None:
        """
        Load an existing key from disk.

        Raises:
            FileNotFoundError: If the key file doesn't exist.
        """
        if not self.key_path.exists():
            raise FileNotFoundError(
                f"Encryption key not found: {self.key_path}\n"
                "Run 'python main.py vault init' to generate a new vault key."
            )
        key = self.key_path.read_bytes()
        self._fernet = Fernet(key)
        logger.info("Loaded encryption key from %s", self.key_path)

    def ensure_key(self) -> None:
        """Load the key if it exists; generate it if not."""
        if self.key_path.exists():
            self.load_key()
        else:
            self.generate_key()

    # ── File operations ───────────────────────────────────────────────────

    def encrypt_file(self, source: Path, destination: Path) -> None:
        """
        Encrypt a file and write the ciphertext to destination.

        Args:
            source: Plaintext file to encrypt.
            destination: Output path for the encrypted file.

        Raises:
            RuntimeError: If the key has not been loaded.
            FileNotFoundError: If source doesn't exist.
        """
        fernet = self._require_key()
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        plaintext = source.read_bytes()
        ciphertext = fernet.encrypt(plaintext)

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(ciphertext)
        logger.info("Encrypted %s → %s (%d bytes)", source.name, destination.name, len(ciphertext))

    def decrypt_file(self, source: Path, destination: Path) -> None:
        """
        Decrypt a Fernet-encrypted file and write plaintext to destination.

        Args:
            source: Encrypted input file.
            destination: Output path for the decrypted file.

        Raises:
            RuntimeError: If the key has not been loaded.
            ValueError: If the file cannot be decrypted (wrong key or corrupted).
        """
        fernet = self._require_key()
        if not source.exists():
            raise FileNotFoundError(f"Encrypted vault not found: {source}")

        try:
            ciphertext = source.read_bytes()
            plaintext = fernet.decrypt(ciphertext)
        except InvalidToken as exc:
            raise ValueError(
                "Decryption failed. The vault may be corrupted or the key is incorrect."
            ) from exc

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(plaintext)
        logger.info("Decrypted %s → %s", source.name, destination.name)

    def encrypt_string(self, plaintext: str) -> bytes:
        """Encrypt a string and return ciphertext bytes."""
        fernet = self._require_key()
        return fernet.encrypt(plaintext.encode())

    def decrypt_string(self, ciphertext: bytes) -> str:
        """Decrypt ciphertext bytes and return a string."""
        fernet = self._require_key()
        try:
            return fernet.decrypt(ciphertext).decode()
        except InvalidToken as exc:
            raise ValueError("Decryption failed.") from exc

    # ── Helpers ───────────────────────────────────────────────────────────

    def _require_key(self) -> Fernet:
        """Return the loaded Fernet instance, or raise if no key is loaded."""
        if self._fernet is None:
            raise RuntimeError("No encryption key loaded. Call load_key() or ensure_key() first.")
        return self._fernet
