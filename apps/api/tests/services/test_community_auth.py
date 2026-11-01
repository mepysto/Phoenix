"""Login link helpers."""

import pytest

from src.services.community.auth import InvalidEmail, hash_token, normalize_email, safe_redirect


def test_normalize_email():
    assert normalize_email("  Alice@Example.ORG ") == "alice@example.org"
    for bad in ["", "nobody", "a@b", "a b@c.org", "a@@c.org"]:
        with pytest.raises(InvalidEmail):
            normalize_email(bad)


def test_safe_redirect_blocks_other_sites():
    assert safe_redirect("/connect") == "/connect"
    for bad in [None, "", "https://evil.example", "//evil.example", "/\\evil", "connect"]:
        assert safe_redirect(bad) == "/"


def test_hash_is_stable_and_not_the_token():
    assert hash_token("abc") == hash_token("abc")
    assert hash_token("abc") != "abc"
    assert len(hash_token("abc")) == 64
