"""Tests for PasswordStrengthChecker."""
import pytest
from src.password_strength import PasswordStrengthChecker, StrengthResult


class TestPasswordStrengthChecker:
    def setup_method(self):
        self.checker = PasswordStrengthChecker()

    def test_very_weak_short_password(self):
        result = self.checker.analyze("abc")
        assert result.score < 40
        assert result.passed is False

    def test_weak_common_password(self):
        result = self.checker.analyze("password123")
        assert result.score < 60
        assert result.passed is False

    def test_strong_password(self):
        result = self.checker.analyze("X7!sT2@jL9#rM4$wQ8%")
        assert result.score >= 60
        assert result.passed is True

    def test_very_strong_long_diverse(self):
        result = self.checker.analyze("T7@xQm!3bLs#9vNp$2kW&dRz")
        assert result.score >= 80
        assert result.label in ("Strong", "Very Strong")

    def test_missing_uppercase_feedback(self):
        result = self.checker.analyze("abc123!@#defghij")
        assert any("uppercase" in tip.lower() for tip in result.feedback)

    def test_missing_digit_feedback(self):
        result = self.checker.analyze("Abcdef!@#XYZqrs")
        assert any("number" in tip.lower() for tip in result.feedback)

    def test_missing_symbol_feedback(self):
        result = self.checker.analyze("AbcDef123GhiJkl")
        assert any("symbol" in tip.lower() for tip in result.feedback)

    def test_short_password_feedback(self):
        result = self.checker.analyze("Ab1!")
        assert any("character" in tip.lower() for tip in result.feedback)

    def test_repeated_chars_penalty(self):
        result_normal = self.checker.analyze("Abc123!@#XyZ")
        result_repeat = self.checker.analyze("Aaa123!@#XyZ")
        assert result_repeat.score <= result_normal.score

    def test_result_has_label(self):
        result = self.checker.analyze("SomeP@ssw0rd!")
        assert isinstance(result.label, str)
        assert len(result.label) > 0

    def test_is_acceptable_strong(self):
        assert self.checker.is_acceptable("X7!sT2@jL9#rM4$wQ8%") is True

    def test_is_acceptable_weak(self):
        assert self.checker.is_acceptable("abc") is False

    def test_score_in_range(self):
        for pw in ["a", "abc123", "P@ssw0rd!", "X7!sT2@jL9#rM4$wQ8%T7@x"]:
            result = self.checker.analyze(pw)
            assert 0 <= result.score <= 100
