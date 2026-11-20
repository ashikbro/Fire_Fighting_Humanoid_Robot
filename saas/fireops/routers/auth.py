"""Sign-up, login, profile and team management."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from ..db import audit, get_conn, now, row, rows
from ..deps import CurrentUser, current_user, require
from ..security import create_token, hash_password, verify_password
from ..services import plan_for

router = APIRouter(prefix="/api/auth", tags=["auth"])
team = APIRouter(prefix="/api/team", tags=["team"])


def _email(v: str) -> str:
    v = v.strip().lower()
    if "@" not in v or "." not in v.split("@")[-1] or len(v) > 200:
        raise ValueError("invalid email address")
    return v


class SignupIn(BaseModel):
    org_name: str = Field(min_length=2, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    email: str
    password: str = Field(min_length=8, max_length=200)
    _v = field_validator("email")(_email)


class LoginIn(BaseModel):
    email: str
    password: str
    _v = field_validator("email")(_email)


class InviteIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str
    password: str = Field(min_length=8, max_length=200)
    role: str = Field(pattern="^(admin|operator|viewer)$")
    _v = field_validator("email")(_email)


class RoleIn(BaseModel):
    role: str = Field(pattern="^(admin|operator|viewer)$")


def _token_response(u: dict) -> dict:
    return {"access_token": create_token(u["id"], u["org_id"], u["role"]), "token_type": "bearer",
            "user": {k: u[k] for k in ("id", "org_id", "email", "name", "role")}}


@router.post("/signup", status_code=201)
def signup(body: SignupIn):
    with get_conn() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email=?", (body.email,)).fetchone():
            raise HTTPException(409, "Email already registered")
        org_id = conn.execute("INSERT INTO orgs (name, plan, created_at) VALUES (?, 'free', ?)",
                              (body.org_name, now())).lastrowid
        uid = conn.execute(
            "INSERT INTO users (org_id, email, name, password_hash, role, created_at) VALUES (?,?,?,?, 'admin', ?)",
            (org_id, body.email, body.name, hash_password(body.password), now())).lastrowid
        conn.execute("INSERT INTO sites (org_id, name, created_at) VALUES (?, 'Main Facility', ?)", (org_id, now()))
        # Sensible default alert rules for a new tenant.
        for name, metric, op, thr, sev in [
            ("Flame detected", "flame", ">=", 1, "high"),
            ("Extreme heat", "temperature", ">=", 80, "critical"),
            ("Toxic gas level", "gas", ">=", 350, "high"),
        ]:
            conn.execute("INSERT INTO alert_rules (org_id, name, metric, op, threshold, severity, created_at) "
                         "VALUES (?,?,?,?,?,?,?)", (org_id, name, metric, op, thr, sev, now()))
        audit(conn, org_id, uid, "org.created", {"name": body.org_name})
        u = row(conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
    return _token_response(u)


@router.post("/login")
def login(body: LoginIn):
    with get_conn() as conn:
        u = row(conn.execute("SELECT * FROM users WHERE email=?", (body.email,)).fetchone())
        if not u or not verify_password(body.password, u["password_hash"]):
            raise HTTPException(401, "Incorrect email or password")
        audit(conn, u["org_id"], u["id"], "user.login")
    return _token_response(u)


@router.get("/me")
def me(user: CurrentUser = Depends(current_user)):
    with get_conn() as conn:
        org = row(conn.execute("SELECT * FROM orgs WHERE id=?", (user.org_id,)).fetchone())
        plan = plan_for(conn, user.org_id)
    return {"user": user.__dict__, "org": org, "plan": plan}


@team.get("")
def list_team(user: CurrentUser = Depends(current_user)):
    with get_conn() as conn:
        return rows(conn.execute("SELECT id, email, name, role, created_at FROM users WHERE org_id=? ORDER BY id",
                                 (user.org_id,)).fetchall())


@team.post("", status_code=201)
def invite(body: InviteIn, user: CurrentUser = Depends(require("admin"))):
    with get_conn() as conn:
        plan = plan_for(conn, user.org_id)
        count = conn.execute("SELECT COUNT(*) FROM users WHERE org_id=?", (user.org_id,)).fetchone()[0]
        if count >= plan["max_users"]:
            raise HTTPException(402, f"Plan '{plan['id']}' allows {plan['max_users']} users. Upgrade to add more.")
        try:
            uid = conn.execute(
                "INSERT INTO users (org_id, email, name, password_hash, role, created_at) VALUES (?,?,?,?,?,?)",
                (user.org_id, body.email, body.name, hash_password(body.password), body.role, now())).lastrowid
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Email already registered")
        audit(conn, user.org_id, user.id, "user.invited", {"email": body.email, "role": body.role})
    return {"id": uid, "email": body.email, "name": body.name, "role": body.role}


@team.patch("/{user_id}")
def change_role(user_id: int, body: RoleIn, user: CurrentUser = Depends(require("admin"))):
    if user_id == user.id and body.role != "admin":
        raise HTTPException(400, "You cannot demote yourself")
    with get_conn() as conn:
        cur = conn.execute("UPDATE users SET role=? WHERE id=? AND org_id=?", (body.role, user_id, user.org_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "User not found")
        audit(conn, user.org_id, user.id, "user.role_changed", {"user_id": user_id, "role": body.role})
    return {"ok": True}


@team.delete("/{user_id}")
def remove_user(user_id: int, user: CurrentUser = Depends(require("admin"))):
    if user_id == user.id:
        raise HTTPException(400, "You cannot remove yourself")
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM users WHERE id=? AND org_id=?", (user_id, user.org_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "User not found")
        audit(conn, user.org_id, user.id, "user.removed", {"user_id": user_id})
    return {"ok": True}
