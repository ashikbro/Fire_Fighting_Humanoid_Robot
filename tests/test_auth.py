import pytest

pytest.importorskip("werkzeug")
from src import auth


@pytest.fixture
def users_file(tmp_path, monkeypatch):
    path = tmp_path / "users.txt"
    monkeypatch.setenv("USERS_FILE", str(path))
    return path


def test_add_user_stores_hash_not_password(users_file):
    auth.add_user("alice", "correct-horse", "admin")
    content = users_file.read_text()
    assert "correct-horse" not in content
    assert content.startswith("alice:")


def test_check_auth(users_file):
    auth.add_user("alice", "correct-horse", "operator")
    users = auth.load_users()
    assert auth.check_auth(users, "alice", "correct-horse")
    assert not auth.check_auth(users, "alice", "wrong")
    assert not auth.check_auth(users, "nobody", "correct-horse")
    assert auth.get_role(users, "alice") == "operator"


def test_add_user_replaces_existing(users_file):
    auth.add_user("alice", "old-password", "viewer")
    auth.add_user("alice", "new-password", "admin")
    users = auth.load_users()
    assert len(users) == 1
    assert auth.check_auth(users, "alice", "new-password")
    assert not auth.check_auth(users, "alice", "old-password")
    assert auth.get_role(users, "alice") == "admin"


def test_plain_text_and_bad_roles_are_rejected(users_file):
    users_file.write_text("eve:plaintext:admin\nmallory:scrypt:x$y:superuser\n")
    assert auth.load_users() == {}


def test_missing_file_means_no_users(users_file):
    assert auth.load_users() == {}


def test_invalid_role_raises(users_file):
    with pytest.raises(ValueError):
        auth.add_user("alice", "pw-123456", "root")
