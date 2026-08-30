import pytest

import auth


def test_authenticate_maps_caller_provenance(tmp_path):
    tokens = tmp_path / "tokens"
    tokens.write_text("opaque-one:alice:user\nopaque-admin:root:admin\n", encoding="utf-8")
    identity = auth.authenticate("Bearer opaque-one", str(tokens))
    assert identity["caller_id"] == "alice"
    assert identity["agent_id"] == "alice"
    assert identity["is_admin"] is False
    assert identity["permissions"] == ["read", "write"]


def test_token_file_is_dynamically_reloaded(tmp_path):
    tokens = tmp_path / "tokens"
    tokens.write_text("first:alice:user\n", encoding="utf-8")
    assert auth.authenticate("first", str(tokens))["name"] == "alice"
    tokens.write_text("second:bob:user\n", encoding="utf-8")
    with pytest.raises(auth.AuthError):
        auth.authenticate("first", str(tokens))
    assert auth.authenticate("second", str(tokens))["name"] == "bob"


def test_hashed_token_verifier_authenticates_without_persisting_bearer(tmp_path):
    raw_token = "opaque-secret-that-must-not-be-persisted"
    verifier = auth.token_verifier(raw_token)
    tokens = tmp_path / "tokens"
    tokens.write_text(f"{verifier}:alice:user\n", encoding="utf-8")

    assert raw_token not in tokens.read_text(encoding="utf-8")
    assert auth.authenticate(raw_token, str(tokens))["caller_id"] == "alice"
    with pytest.raises(auth.AuthError):
        auth.authenticate("wrong-token", str(tokens))


def test_malformed_hashed_verifier_is_ignored_during_authentication(tmp_path):
    tokens = tmp_path / "tokens"
    tokens.write_text("sha256$short:alice:user\n", encoding="utf-8")
    with pytest.raises(auth.AuthError):
        auth.authenticate("short", str(tokens))


def test_malformed_or_unknown_tokens_are_rejected(tmp_path):
    tokens = tmp_path / "tokens"
    tokens.write_text("bad-line\nknown:alice:user\nignored:bob:owner\n", encoding="utf-8")
    with pytest.raises(auth.AuthError):
        auth.authenticate("unknown", str(tokens))
    with pytest.raises(auth.AuthError):
        auth.authenticate("ignored", str(tokens))
