import hashlib
import os
import secrets
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import yaml
from fastapi import Cookie, HTTPException, status

from backend.db import db

SESSION_COOKIE = "sovereign_session"
SESSION_DAYS = int(os.getenv("AUTH_SESSION_DAYS", "7"))
AUTH_FILE = Path(__file__).resolve().parent.parent / "frontend" / "auth.yaml"


def _credentials():
    with AUTH_FILE.open(encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    return config.get("credentials", {}).get("usernames", {})


def authenticate(username: str, password: str):
    record = _credentials().get(username)
    stored_user = db.get_user(username)
    if not record and not stored_user:
        return None
    stored_hash = (stored_user or {}).get("password_hash") or (record or {}).get("password", "")
    stored_hash = stored_hash.encode("utf-8")
    if not stored_hash or not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
        return None
    user = {
        "username": username,
        "name": (stored_user or {}).get("name") or (record or {}).get("name", username),
        "email": (stored_user or {}).get("email") or (record or {}).get("email", ""),
    }
    db.ensure_user(username, user["name"], user["email"], (record or {}).get("password"))
    retention_days = (db.get_user(username) or {}).get("session_retention_days") or 30
    expired_sessions = db.cleanup_expired_sessions(username, retention_days)
    workspace_root = Path(__file__).resolve().parent.parent / "workspace"
    for session_id in expired_sessions:
        shutil.rmtree(workspace_root / f"session_{session_id}", ignore_errors=True)
    return user


def create_session(username: str):
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    db.create_auth_session(token_hash, username, expires_at.isoformat())
    return raw_token


def delete_session(raw_token: str | None):
    if raw_token:
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        db.delete_auth_session(token_hash)


def current_user(sovereign_session: str | None = Cookie(default=None)):
    if not sovereign_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    token_hash = hashlib.sha256(sovereign_session.encode("utf-8")).hexdigest()
    session = db.get_auth_session(token_hash)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    record = _credentials().get(session["username"])
    stored_user = db.get_user(session["username"])
    if not record and not stored_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is unavailable")
    return {
        "username": session["username"],
        "name": (stored_user or {}).get("name") or record.get("name", session["username"]),
        "email": (stored_user or {}).get("email") or record.get("email", ""),
    }


def user_settings(username: str):
    user = db.get_user(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {
        "username": user["username"],
        "name": user["name"],
        "email": user["email"],
        "theme": user.get("theme") or "dark",
        "default_model": user.get("default_model") or "auto",
        "default_temperature": user.get("default_temperature") if user.get("default_temperature") is not None else 0.0,
        "default_num_ctx": user.get("default_num_ctx") or 8192,
        "default_system_prompt": user.get("default_system_prompt") or "",
        "default_landing_page": user.get("default_landing_page") or "chat",
        "session_retention_days": user.get("session_retention_days") or 30,
    }


def verify_password(username: str, password: str):
    user = db.get_user(username)
    stored_hash = (user or {}).get("password_hash")
    return bool(stored_hash and bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")))


def hash_password(password: str):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def register_user(username: str, name: str, email: str, password: str):
    username = username.strip().lower()
    name = name.strip()
    email = email.strip().lower()
    if len(username) < 3 or not username.replace("_", "").isalnum():
        raise ValueError("Username must be at least 3 characters and use letters, numbers, or underscores")
    if not name:
        raise ValueError("Display name is required")
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise ValueError("Enter a valid email address")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if db.user_exists(username) or username in _credentials():
        raise ValueError("Username is already registered")
    db.create_user(username, name, email, hash_password(password))
    return {"username": username, "name": name, "email": email}
