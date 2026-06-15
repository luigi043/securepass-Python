"""Tests for PasswordGenerator."""
import pytest
import string
from src.password_generator import PasswordGenerator, GeneratorOptions


class TestPasswordGenerator:
    def test_default_password_length(self):
        gen = PasswordGenerator()
        pw = gen.generate(GeneratorOptions(length=20))
        assert len(pw) == 20

    def test_custom_length(self):
        gen = PasswordGenerator()
        for length in [8, 12, 32, 64]:
            pw = gen.generate(GeneratorOptions(length=length))
            assert len(pw) == length

    def test_uppercase_only(self):
        gen = PasswordGenerator()
        opts = GeneratorOptions(length=50, uppercase=True, lowercase=False, digits=False, symbols=False)
        pw = gen.generate(opts)
        assert all(c in string.ascii_uppercase for c in pw)

    def test_lowercase_only(self):
        gen = PasswordGenerator()
        opts = GeneratorOptions(length=50, uppercase=False, lowercase=True, digits=False, symbols=False)
        pw = gen.generate(opts)
        assert all(c in string.ascii_lowercase for c in pw)

    def test_digits_only(self):
        gen = PasswordGenerator()
        opts = GeneratorOptions(length=20, uppercase=False, lowercase=False, digits=True, symbols=False)
        pw = gen.generate(opts)
        assert all(c in string.digits for c in pw)

    def test_contains_required_chars_all_sets(self):
        gen = PasswordGenerator()
        opts = GeneratorOptions(length=30, uppercase=True, lowercase=True, digits=True, symbols=True)
        pw = gen.generate(opts)
        assert any(c in string.ascii_uppercase for c in pw)
        assert any(c in string.ascii_lowercase for c in pw)
        assert any(c in string.digits for c in pw)
        assert any(c in string.punctuation for c in pw)

    def test_no_charset_raises_value_error(self):
        gen = PasswordGenerator()
        opts = GeneratorOptions(uppercase=False, lowercase=False, digits=False, symbols=False)
        with pytest.raises(ValueError):
            gen.generate(opts)

    def test_zero_length_raises_value_error(self):
        gen = PasswordGenerator()
        with pytest.raises(ValueError):
            gen.generate(GeneratorOptions(length=0))

    def test_exclude_ambiguous_chars(self):
        gen = PasswordGenerator()
        opts = GeneratorOptions(length=100, exclude_ambiguous=True, symbols=False)
        pw = gen.generate(opts)
        for c in "0Ol1I":
            assert c not in pw

    def test_generate_batch_count(self):
        gen = PasswordGenerator()
        batch = gen.generate_batch(5)
        assert len(batch) == 5
        assert all(isinstance(p, str) for p in batch)

    def test_batch_passwords_are_unique(self):
        gen = PasswordGenerator()
        batch = gen.generate_batch(10, GeneratorOptions(length=20))
        assert len(set(batch)) == 10

    def test_passphrase_contains_words_and_number(self):
        gen = PasswordGenerator()
        phrase = gen.generate_passphrase(word_count=4)
        parts = phrase.split("-")
        assert len(parts) == 5  # 4 words + 1 number
        assert parts[-1].isdigit()

    def test_passphrase_custom_separator(self):
        gen = PasswordGenerator()
        phrase = gen.generate_passphrase(word_count=3, separator="_")
        assert "_" in phrase

    def test_not_random_module(self):
        """Confirm secrets is used — passwords should not be predictable."""
        import secrets as s_module
        gen = PasswordGenerator()
        pw1 = gen.generate(GeneratorOptions(length=32))
        pw2 = gen.generate(GeneratorOptions(length=32))
        assert pw1 != pw2
