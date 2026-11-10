"""User authentication for the robot control API.

Users live in a file that is NOT committed to git (see ``USERS_FILE`` in
``.env.example``). Each line has the form::

    username:password_hash:role

where ``role`` is one of ``admin``, ``operator`` or ``viewer`` and
``password_hash`` is a werkzeug hash. Plain-text passwords are rejected.

Create or update a user with::

    python -m src.auth add <username> <role>

You will be prompted for the password; only its hash is written to the file.
"""

import argparse
import getpass
import logging
import os
import sys

from werkzeug.security import check_password_hash, generate_password_hash

ROLES = ("admin", "operator", "viewer")
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_KNOWN_HASH_PREFIXES = ("scrypt:", "pbkdf2:")

logger = logging.getLogger(__name__)


def users_file_path():
    """Return the path of the users file (``USERS_FILE`` env var, default ``users.txt``)."""
    path = os.getenv("USERS_FILE", "users.txt")
    return path if os.path.isabs(path) else os.path.join(_REPO_ROOT, path)


def load_users(path=None):
    """Load users from ``path``. Returns ``{username: {"hash": ..., "role": ...}}``.

    A missing file yields no users (every protected endpoint then returns 401).
    Lines with an unknown role or a plain-text password are skipped with a warning.
    """
    path = path or users_file_path()
    users = {}
    if not os.path.exists(path):
        logger.warning("Users file %s not found; no users can log in. "
                       "Create one with: python -m src.auth add <username> <role>", path)
        return users
    with open(path) as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # The hash itself contains ':' (e.g. "scrypt:32768:8:1$..."), so split
            # off the username from the left and the role from the right.
            try:
                username, rest = line.split(":", 1)
                pw_hash, role = rest.rsplit(":", 1)
            except ValueError:
                logger.warning("%s:%d: malformed line, skipped", path, lineno)
                continue
            if role not in ROLES:
                logger.warning("%s:%d: unknown role %r, skipped", path, lineno, role)
                continue
            if not pw_hash.startswith(_KNOWN_HASH_PREFIXES):
                logger.warning("%s:%d: password for %r is not hashed, skipped. "
                               "Re-create it with: python -m src.auth add %s %s",
                               path, lineno, username, username, role)
                continue
            users[username] = {"hash": pw_hash, "role": role}
    return users


def check_auth(users, username, password):
    """Return True if ``username``/``password`` match an entry in ``users``."""
    user = users.get(username)
    return bool(user) and check_password_hash(user["hash"], password)


def get_role(users, username):
    user = users.get(username)
    return user["role"] if user else None


def add_user(username, password, role, path=None):
    """Add or replace ``username`` in the users file, storing only a password hash."""
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    if ":" in username:
        raise ValueError("username may not contain ':'")
    path = path or users_file_path()
    lines = []
    if os.path.exists(path):
        with open(path) as f:
            lines = [l for l in f.read().splitlines() if l.split(":", 1)[0] != username]
    lines.append(f"{username}:{generate_password_hash(password)}:{role}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _main(argv=None):
    parser = argparse.ArgumentParser(description="Manage API users.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add", help="add or update a user")
    add.add_argument("username")
    add.add_argument("role", choices=ROLES)
    args = parser.parse_args(argv)

    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Repeat password: "):
        sys.exit("Passwords do not match.")
    if len(password) < 8:
        sys.exit("Password must be at least 8 characters.")
    add_user(args.username, password, args.role)
    print(f"Saved user {args.username!r} ({args.role}) to {users_file_path()}")


if __name__ == "__main__":
    _main()
