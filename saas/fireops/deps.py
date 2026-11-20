"""FastAPI dependencies for user (JWT) and device (API key) authentication."""
from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException, status

from .db import get_conn, row
from .security import decode_token, hash_device_key

ROLE_RANK = {"viewer": 0, "operator": 1, "admin": 2}


@dataclass
class CurrentUser:
    id: int
    org_id: int
    role: str
    email: str
    name: str


def _user_from_token(token: str) -> CurrentUser:
    try:
        claims = decode_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    with get_conn() as conn:
        u = row(conn.execute("SELECT * FROM users WHERE id=?", (int(claims["sub"]),)).fetchone())
    if not u or u["org_id"] != claims["org"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    return CurrentUser(u["id"], u["org_id"], u["role"], u["email"], u["name"])


def current_user(authorization: str = Header(default="")) -> CurrentUser:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token",
                            headers={"WWW-Authenticate": "Bearer"})
    return _user_from_token(token)


def require(role: str):
    def checker(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if ROLE_RANK[user.role] < ROLE_RANK[role]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires {role} role")
        return user
    return checker


def current_robot(x_device_key: str = Header(default="")) -> dict:
    if not x_device_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing X-Device-Key header")
    with get_conn() as conn:
        r = row(conn.execute("SELECT * FROM robots WHERE api_key_hash=?",
                             (hash_device_key(x_device_key),)).fetchone())
    if not r:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown device key")
    return r
