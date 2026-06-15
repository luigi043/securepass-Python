"""Tests for EncryptionService."""
import pytest
from pathlib import Path
from src.encryption_service import EncryptionService


@pytest.fixture
def svc(tmp_path):
    s = EncryptionService(key_path=tmp_path / ".vault.key")
    s.generate_key()
    return s


class TestEncryptionService:
    def test_generate_key_creates_file(self, tmp_path):
        svc = EncryptionService(tmp_path / ".vault.key")
        svc.generate_key()
        assert (tmp_path / ".vault.key").exists()

    def test_load_key_success(self, tmp_path):
        svc = EncryptionService(tmp_path / ".vault.key")
        svc.generate_key()
        svc2 = EncryptionService(tmp_path / ".vault.key")
        svc2.load_key()  # Should not raise

    def test_load_missing_key_raises(self, tmp_path):
        svc = EncryptionService(tmp_path / ".no.key")
        with pytest.raises(FileNotFoundError):
            svc.load_key()

    def test_encrypt_decrypt_file_roundtrip(self, svc, tmp_path):
        src = tmp_path / "accounts.csv"
        src.write_text("username,email\njohn,john@example.com")
        enc = tmp_path / "vault.dat"
        dec = tmp_path / "restored.csv"
        svc.encrypt_file(src, enc)
        svc.decrypt_file(enc, dec)
        assert dec.read_text() == src.read_text()

    def test_encrypted_file_differs_from_source(self, svc, tmp_path):
        src = tmp_path / "data.csv"
        src.write_text("secret data here")
        enc = tmp_path / "vault.dat"
        svc.encrypt_file(src, enc)
        assert src.read_bytes() != enc.read_bytes()

    def test_encrypt_string_roundtrip(self, svc):
        plain = "SuperSecretValue123!"
        cipher = svc.encrypt_string(plain)
        assert svc.decrypt_string(cipher) == plain

    def test_decrypt_wrong_key_raises(self, tmp_path):
        svc1 = EncryptionService(tmp_path / "key1.key")
        svc1.generate_key()
        svc2 = EncryptionService(tmp_path / "key2.key")
        svc2.generate_key()
        src = tmp_path / "data.csv"
        src.write_text("hello")
        enc = tmp_path / "vault.dat"
        svc1.encrypt_file(src, enc)
        with pytest.raises(ValueError):
            svc2.decrypt_file(enc, tmp_path / "out.csv")

    def test_require_key_raises_without_load(self, tmp_path):
        svc = EncryptionService(tmp_path / ".vault.key")
        with pytest.raises(RuntimeError):
            svc.encrypt_string("test")
