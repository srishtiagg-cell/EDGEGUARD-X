"""Local authentication and append-only CSV activity logging for EDGEGUARD-X."""

from __future__ import annotations

import csv
import hashlib
import hmac
import json
import os
import secrets
import shutil
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
USERS_FILE = BASE_DIR / "users.json"
ACCESS_LOG = BASE_DIR / "user_access_log.csv"
ACTIVITY_LOG = BASE_DIR / "activity_log.csv"
ACCESS_COLUMNS = ["timestamp_local", "user_id", "action"]
ACTIVITY_COLUMNS = ["timestamp_local", "user_id", "category", "action", "details"]
PBKDF2_ITERATIONS = 600_000


class UnsupportedPasswordScheme(Exception):
    """Raised when a user record has no explicitly identified hash scheme."""


def _timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _append_csv(path: Path, columns: list[str], row: dict[str, str]) -> None:
    """Append one row, preserving existing contents and writing a header if absent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        if needs_header:
            writer.writeheader()
        writer.writerow({column: row.get(column, "") for column in columns})


def log_access(user_id: str, action: str) -> None:
    _append_csv(ACCESS_LOG, ACCESS_COLUMNS, {
        "timestamp_local": _timestamp(), "user_id": user_id, "action": action,
    })


def log_activity(user_id: str, category: str, action: str, details: str = "") -> None:
    # Callers must pass non-secret descriptive details only.
    _append_csv(ACTIVITY_LOG, ACTIVITY_COLUMNS, {
        "timestamp_local": _timestamp(), "user_id": user_id,
        "category": category, "action": action, "details": details,
    })


def _read_users() -> dict:
    with USERS_FILE.open("r", encoding="utf-8") as handle:
        users = json.load(handle)
    if not isinstance(users, dict):
        raise ValueError("users.json must contain a JSON object.")
    return users


def verify_login(user_id: str, password: str) -> tuple[bool, str | None]:
    """Verify explicit PBKDF2-SHA256 records; never infer legacy algorithms."""
    candidate_id = user_id.strip().casefold()
    users = _read_users()
    record = next((value for key, value in users.items() if str(key).casefold() == candidate_id), None)
    if not isinstance(record, dict):
        return False, None

    scheme = record.get("password_scheme")
    if scheme != "pbkdf2_sha256":
        raise UnsupportedPasswordScheme(
            "This account uses a legacy password record whose algorithm is not identified. "
            "The record was left unchanged. An administrator must identify its original "
            "verifier or perform an explicitly authorized password migration."
        )

    salt_hex = record.get("salt", "")
    expected_hex = record.get("password_hash", "")
    try:
        salt = bytes.fromhex(salt_hex)
        iterations = int(record["iterations"])
        expected = bytes.fromhex(expected_hex)
    except (ValueError, TypeError, KeyError):
        return False, None
    if iterations < 100_000 or len(expected) != 32 or len(salt) < 16:
        return False, None
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    if not hmac.compare_digest(actual, expected):
        return False, None
    return True, str(record.get("role", "user"))


def make_password_record(password: str, role: str = "user") -> dict[str, str | int]:
    """Create a new record using the supported local password scheme."""
    if len(password) < 12:
        raise ValueError("Passwords must contain at least 12 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return {
        "salt": salt.hex(), "password_hash": digest.hex(),
        "password_scheme": "pbkdf2_sha256", "iterations": PBKDF2_ITERATIONS,
        "role": role,
    }


def save_user(user_id: str, password: str, role: str = "user") -> None:
    """Add a new account without modifying existing records."""
    clean_id = user_id.strip()
    if not clean_id or clean_id in {".", ".."}:
        raise ValueError("Enter a valid user ID.")
    users = _read_users()
    key = clean_id.casefold()
    if key in {str(existing).casefold() for existing in users}:
        raise ValueError("That user ID already exists.")
    users[key] = {"user_id": clean_id, **make_password_record(password, role)}
    temporary = USERS_FILE.with_name(USERS_FILE.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(users, handle, indent=2)
        handle.write("\n")
    os.replace(temporary, USERS_FILE)


def recover_admin_password(password: str, *, ownership_confirmed: bool, confirmation: str) -> Path:
    """Explicitly replace only the existing admin verifier, after backing up users.json."""
    if not ownership_confirmed or confirmation != "RESET ADMIN PASSWORD":
        raise ValueError("Confirm local project ownership and enter RESET ADMIN PASSWORD.")
    replacement = make_password_record(password, role="admin")
    users = _read_users()
    admin_key = next((key for key in users if str(key).casefold() == "admin"), None)
    record = users.get(admin_key) if admin_key is not None else None
    if not isinstance(record, dict):
        raise ValueError("No existing admin account was found; recovery will not create one.")
    if not USERS_FILE.is_file():
        raise ValueError("users.json is missing; recovery will not create an account store.")

    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")
    backup = USERS_FILE.with_name(f"{USERS_FILE.name}.backup-{stamp}")
    shutil.copy2(USERS_FILE, backup)
    updated = dict(users)
    updated[admin_key] = {"user_id": str(record.get("user_id") or "admin"), **replacement}
    temporary = USERS_FILE.with_name(USERS_FILE.name + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(updated, handle, indent=2)
            handle.write("\n")
        os.replace(temporary, USERS_FILE)
    finally:
        if temporary.exists():
            temporary.unlink()

    log_activity("admin", "security", "admin_password_recovered", f"Explicit local recovery; backup={backup.name}")
    return backup

