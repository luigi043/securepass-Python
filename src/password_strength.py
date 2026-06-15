"""
PasswordStrengthChecker
=======================
Scores password strength on a 0–100 scale and returns human-readable feedback.
Detects common patterns, dictionary words, and character diversity.
"""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Common patterns that weaken passwords
COMMON_PATTERNS: list[str] = [
    r"password", r"admin", r"welcome", r"letmein", r"qwerty",
    r"123456", r"abcdef", r"111111", r"000000",
    r"(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)",
    r"(012|123|234|345|456|567|678|789|890)",
]

STRENGTH_LABELS = {
    (0, 20):   "Very Weak",
    (20, 40):  "Weak",
    (40, 60):  "Fair",
    (60, 80):  "Strong",
    (80, 101): "Very Strong",
}


@dataclass
class StrengthResult:
    """Result of a password strength analysis."""
    score: int                          # 0–100
    label: str                          # Human-readable label
    feedback: list[str] = field(default_factory=list)   # Improvement tips
    passed: bool = False                # True if score >= 60


class PasswordStrengthChecker:
    """
    Evaluates password strength using multiple heuristics:
    - Length scoring
    - Character diversity
    - Common pattern detection
    - Entropy estimation
    """

    MIN_ACCEPTABLE_SCORE = 60

    def analyze(self, password: str) -> StrengthResult:
        """
        Analyze a password and return a StrengthResult.

        Args:
            password: The password string to evaluate.

        Returns:
            StrengthResult with score, label, and actionable feedback.
        """
        score = 0
        feedback: list[str] = []

        # ── Length scoring (max 30 pts) ───────────────────────────────────
        length = len(password)
        if length < 8:
            feedback.append("Use at least 8 characters.")
        elif length < 12:
            score += 10
            feedback.append("Consider using 12+ characters for better security.")
        elif length < 16:
            score += 20
        elif length < 24:
            score += 25
        else:
            score += 30

        # ── Character diversity (max 40 pts) ──────────────────────────────
        has_upper = bool(re.search(r"[A-Z]", password))
        has_lower = bool(re.search(r"[a-z]", password))
        has_digit = bool(re.search(r"\d", password))
        has_symbol = bool(re.search(r"[^a-zA-Z0-9]", password))

        diversity_count = sum([has_upper, has_lower, has_digit, has_symbol])
        score += diversity_count * 10

        if not has_upper:
            feedback.append("Add uppercase letters (A–Z).")
        if not has_lower:
            feedback.append("Add lowercase letters (a–z).")
        if not has_digit:
            feedback.append("Add numbers (0–9).")
        if not has_symbol:
            feedback.append("Add symbols (!, @, #, ...).")

        # ── Common patterns (penalty, max −30 pts) ────────────────────────
        lower_pw = password.lower()
        pattern_hits = 0
        for pattern in COMMON_PATTERNS:
            if re.search(pattern, lower_pw):
                pattern_hits += 1

        if pattern_hits:
            penalty = min(30, pattern_hits * 10)
            score = max(0, score - penalty)
            feedback.append("Avoid common words, sequences, or keyboard patterns.")

        # ── Repeated characters penalty ────────────────────────────────────
        if re.search(r"(.)\1{2,}", password):
            score = max(0, score - 10)
            feedback.append("Avoid repeating the same character 3+ times.")

        # ── Bonus for extra length + full diversity ───────────────────────
        if length >= 20 and diversity_count == 4:
            score = min(100, score + 10)

        score = max(0, min(100, score))

        # ── Determine label ───────────────────────────────────────────────
        label = "Unknown"
        for (low, high), lbl in STRENGTH_LABELS.items():
            if low <= score < high:
                label = lbl
                break

        if not feedback:
            feedback.append("Great password! Keep it secret and don't reuse it.")

        result = StrengthResult(
            score=score,
            label=label,
            feedback=feedback,
            passed=score >= self.MIN_ACCEPTABLE_SCORE,
        )
        logger.debug("Password strength score: %d (%s)", score, label)
        return result

    def is_acceptable(self, password: str) -> bool:
        """Quick check — returns True if password meets minimum standards."""
        return self.analyze(password).passed
