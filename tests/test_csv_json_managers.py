"""Tests for CSVManager and JSONManager."""

import pytest

from src.account_manager import AccountManager
from src.csv_manager import CSVManager
from src.json_manager import JSONManager


@pytest.fixture
def sample_accounts():
    mgr = AccountManager()
    mgr.add("github.com", username="jdoe", email="j@example.com", password="P@ss1!XyZ", expiry_days=90)
    mgr.add("gmail.com", username="jdoe2", email="j2@example.com", password="An0ther!P@ss", expiry_days=60)
    return mgr.list_all()


class TestCSVManager:
    def test_save_and_load_roundtrip(self, tmp_path, sample_accounts):
        csv = CSVManager(tmp_path / "accounts.csv")
        csv.save(sample_accounts)
        loaded = csv.load()
        assert len(loaded) == 2
        websites = {a.website for a in loaded}
        assert "github.com" in websites
        assert "gmail.com" in websites

    def test_load_missing_file_returns_empty(self, tmp_path):
        csv = CSVManager(tmp_path / "nonexistent.csv")
        assert csv.load() == []

    def test_saved_file_exists(self, tmp_path, sample_accounts):
        path = tmp_path / "accounts.csv"
        csv = CSVManager(path)
        csv.save(sample_accounts)
        assert path.exists()

    def test_fields_preserved(self, tmp_path, sample_accounts):
        csv = CSVManager(tmp_path / "accounts.csv")
        csv.save(sample_accounts)
        loaded = csv.load()
        original = {a.id: a for a in sample_accounts}
        for a in loaded:
            assert a.username == original[a.id].username
            assert a.website == original[a.id].website


class TestJSONManager:
    def test_save_and_load_roundtrip(self, tmp_path, sample_accounts):
        jm = JSONManager(tmp_path / "accounts.json")
        jm.save(sample_accounts)
        loaded = jm.load()
        assert len(loaded) == 2

    def test_load_missing_returns_empty(self, tmp_path):
        jm = JSONManager(tmp_path / "missing.json")
        assert jm.load() == []

    def test_json_is_valid_structure(self, tmp_path, sample_accounts):
        import json
        path = tmp_path / "accounts.json"
        jm = JSONManager(path)
        jm.save(sample_accounts)
        data = json.loads(path.read_text())
        assert isinstance(data, list)
        assert "website" in data[0]

    def test_corrupt_json_returns_empty(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("NOT JSON {{{{")
        jm = JSONManager(path)
        assert jm.load() == []
