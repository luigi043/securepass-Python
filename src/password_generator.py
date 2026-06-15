"""
PasswordGenerator
=================
Generates cryptographically secure passwords using the `secrets` module.
Never uses `random` — secrets is designed for security-sensitive applications.
"""

import secrets
import string
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Common weak passwords to always block
WEAK_PASSWORDS: set[str] = {
    "password", "password123", "admin", "admin123", "welcome",
    "welcome123", "123456", "12345678", "qwerty", "letmein",
    "monkey", "iloveyou", "sunshine", "princess", "dragon",
}


@dataclass
class GeneratorOptions:
    """Configuration options for password generation."""
    length: int = 20
    uppercase: bool = True
    lowercase: bool = True
    digits: bool = True
    symbols: bool = True
    exclude_ambiguous: bool = False  # Exclude 0, O, l, 1, I


class PasswordGenerator:
    """
    Generates cryptographically secure passwords.

    Uses Python's `secrets` module which is backed by the OS CSPRNG,
    making it safe for security-sensitive use cases.
    """

    AMBIGUOUS_CHARS = "0Ol1I"

    def __init__(self, options: GeneratorOptions | None = None) -> None:
        self.options = options or GeneratorOptions()

    def generate(self, options: GeneratorOptions | None = None) -> str:
        """
        Generate a single cryptographically secure password.

        Args:
            options: Override default options for this call.

        Returns:
            A secure password string.

        Raises:
            ValueError: If no character sets are selected or length is invalid.
        """
        opts = options or self.options
        charset = self._build_charset(opts)

        if not charset:
            raise ValueError("At least one character set must be enabled.")
        if opts.length < 1:
            raise ValueError(f"Password length must be >= 1, got {opts.length}.")

        # Guarantee at least one char from each enabled group (policy compliance)
        required = self._required_chars(opts)

        while True:
            # Fill remainder with random chars from full charset
            remaining = opts.length - len(required)
            password_chars = required + [secrets.choice(charset) for _ in range(remaining)]
            # Shuffle to avoid predictable positions for required chars
            secrets.SystemRandom().shuffle(password_chars)
            password = "".join(password_chars)

            # Reject if it matches a known weak password
            if password.lower() not in WEAK_PASSWORDS:
                logger.debug("Generated password of length %d", opts.length)
                return password

    def generate_passphrase(self, word_count: int = 4, separator: str = "-") -> str:
        """
        Generate a memorable passphrase from random words.

        Uses a built-in word list for offline operation.

        Args:
            word_count: Number of words (default 4).
            separator: Character between words (default '-').

        Returns:
            A passphrase like 'tiger-sunset-marble-42'.
        """
        words = [
            "tiger", "sunset", "marble", "river", "falcon", "silver", "storm",
            "glacier", "nova", "forge", "ember", "cipher", "delta", "iron",
            "nebula", "prism", "vault", "lunar", "frost", "echo", "raven",
            "cobalt", "quartz", "tempest", "zenith", "onyx", "amber", "cedar",
        ]
        chosen = [secrets.choice(words) for _ in range(word_count)]
        chosen.append(str(secrets.randbelow(99) + 1))
        return separator.join(chosen)

    def generate_batch(self, count: int, options: GeneratorOptions | None = None) -> list[str]:
        """Generate multiple passwords at once."""
        return [self.generate(options) for _ in range(count)]

    # ── Private helpers ────────────────────────────────────────────────────

    def _enabled_pools(self, opts: GeneratorOptions) -> list[str]:
        """Return the character pool for each enabled group, in fixed order."""
        pools: list[str] = []
        if opts.uppercase:
            pools.append(string.ascii_uppercase)
        if opts.lowercase:
            pools.append(string.ascii_lowercase)
        if opts.digits:
            pools.append(string.digits)
        if opts.symbols:
            pools.append(string.punctuation)
        if opts.exclude_ambiguous:
            pools = [self._strip_ambiguous(pool) for pool in pools]
        return pools

    def _strip_ambiguous(self, chars: str) -> str:
        """Remove visually ambiguous characters (0, O, l, 1, I) from a pool."""
        return "".join(c for c in chars if c not in self.AMBIGUOUS_CHARS)

    def _build_charset(self, opts: GeneratorOptions) -> str:
        """Assemble the character set from enabled options."""
        return "".join(self._enabled_pools(opts))

    def _required_chars(self, opts: GeneratorOptions) -> list[str]:
        """Return one guaranteed character per enabled group."""
        return [secrets.choice(pool) for pool in self._enabled_pools(opts)]
