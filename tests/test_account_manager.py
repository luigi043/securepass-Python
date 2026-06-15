"""Tests for AccountManager."""
from datetime import datetime, timedelta

import pytest

from src.account_manager import AccountManager


class TestAccountManager:
    def setup_method(self):
        self.mgr = AccountManager(max_history=3)

    def _add(self, website="github.com", username="jdoe", password="P@ss1!XyZ"):
        return self.mgr.add(
            username=username, email="j@example.com",
            website=website, password=password, expiry_days=90
        )

    def test_add_creates_account(self):
        a = self._add()
        assert a.id in [acc.id for acc in self.mgr.list_all()]

    def test_add_sets_created_at(self):
        a = self._add()
        assert a.created_at != ""

    def test_add_sets_expiry(self):
        a = self._add()
        assert a.expires_at != ""

    def test_add_no_expiry(self):
        a = self.mgr.add("site.com", username="u", email="", password="P@ss1!X", expiry_days=0)
        assert a.expires_at == ""

    def test_get_returns_account(self):
        a = self._add()
        found = self.mgr.get(a.id)
        assert found is not None
        assert found.id == a.id

    def test_get_missing_returns_none(self):
        assert self.mgr.get("nonexistent-id") is None

    def test_delete_removes_account(self):
        a = self._add()
        self.mgr.delete(a.id)
        assert self.mgr.get(a.id) is None

    def test_delete_missing_raises_key_error(self):
        with pytest.raises(KeyError):
            self.mgr.delete("nonexistent")

    def test_update_username(self):
        a = self._add()
        updated = self.mgr.update(a.id, username="newuser")
        assert updated.username == "newuser"

    def test_update_password_tracks_history(self):
        a = self._add(password="OldP@ss1!")
        self.mgr.update(a.id, password="NewP@ss2!")
        assert len(a.password_history) == 2

    def test_update_reused_password_raises(self):
        a = self._add(password="OldP@ss1!")
        with pytest.raises(ValueError):
            self.mgr.update(a.id, password="OldP@ss1!")

    def test_history_trimmed_to_max(self):
        a = self._add(password="P@ss0!Xy")
        for i in range(5):
            self.mgr.update(a.id, password=f"P@ssw0rd{i}!X")
        assert len(a.password_history) <= 3

    def test_search_by_website(self):
        self._add(website="github.com")
        self._add(website="gitlab.com")
        results = self.mgr.search("github")
        assert len(results) == 1
        assert results[0].website == "github.com"

    def test_search_case_insensitive(self):
        self._add(website="GitHub.com")
        results = self.mgr.search("github")
        assert len(results) == 1

    def test_search_no_match(self):
        self._add(website="github.com")
        assert self.mgr.search("twitter") == []

    def test_list_all_sorted_by_website(self):
        self._add(website="zzz.com")
        self._add(website="aaa.com")
        names = [a.website for a in self.mgr.list_all()]
        assert names == sorted(names, key=str.lower)

    def test_is_expired_false_future(self):
        a = self._add()
        assert a.is_expired is False

    def test_is_expired_true_past(self):
        a = self.mgr.add("x.com", username="u", email="", password="P@ss1!X", expiry_days=0)
        a.expires_at = (datetime.now() - timedelta(days=1)).isoformat()
        assert a.is_expired is True

    def test_days_until_expiry_positive(self):
        a = self._add()
        days = a.days_until_expiry()
        assert days is not None and days > 0

    def test_load_from_list(self):
        a = self._add()
        new_mgr = AccountManager()
        new_mgr.load_from_list([a])
        assert new_mgr.get(a.id) is not None
