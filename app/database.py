"""
SQLite database management for candidates, clients, submissions, and settings.
Kept in data/cv_modifier.db next to the application.
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.config import DB_PATH, ASSETS_DIR, ensure_directories, DEFAULT_SETTINGS
from app.logger import logger


def get_connection() -> sqlite3.Connection:
    """Creates or returns a SQLite connection with row factory enabled and WAL mode."""
    ensure_directories()
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # Settings table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    # Candidates table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            original_filename TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    # Clients table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT,
            email TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    # Submissions table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            candidate_code TEXT NOT NULL,
            candidate_role TEXT NOT NULL,
            client_id INTEGER,
            client_name TEXT NOT NULL,
            client_email TEXT NOT NULL,
            cv_filename TEXT NOT NULL,
            cv_path TEXT NOT NULL,
            sent_at TEXT NOT NULL,
            status TEXT NOT NULL,  -- 'sent', 'failed'
            error_message TEXT,
            email_subject TEXT,
            FOREIGN KEY(candidate_id) REFERENCES candidates(id),
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
        """
    )

    # Users table (Local offline auth with salted PBKDF2 hashes)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Recruiter',
            created_at TEXT NOT NULL,
            failed_attempts INTEGER DEFAULT 0,
            locked_until REAL DEFAULT 0
        )
        """
    )

    conn.commit()

    # Seed default settings if empty or update default logo
    for k, v in DEFAULT_SETTINGS.items():
        cursor.execute("SELECT value FROM settings WHERE key = ?", (k,))

        row = cursor.fetchone()
        if not row:
            cursor.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?)",
                (k, json.dumps(v)),
            )
        elif k == "logo_path":
            val = json.loads(row["value"])
            default_logo = str(ASSETS_DIR / "scalexpro_logo.png")
            # If empty or file doesn't exist, automatically use default scalexpro logo
            if (not val or not os.path.exists(val)) and os.path.exists(default_logo):
                cursor.execute(
                    "UPDATE settings SET value = ? WHERE key = ?",
                    (json.dumps(default_logo), k),
                )
        elif k == "company_name":
            val = json.loads(row["value"])
            if val in ("Apex Talent Partners", ""):
                cursor.execute(
                    "UPDATE settings SET value = ? WHERE key = ?",
                    (json.dumps("ScaleXPro"), k),
                )

    # Ensure client status column exists
    try:
        cursor.execute("ALTER TABLE clients ADD COLUMN status TEXT DEFAULT 'Active'")
    except Exception:
        pass

    # Seed initial submissions if empty
    cursor.execute("SELECT COUNT(*) as cnt FROM submissions")
    sub_count = cursor.fetchone()["cnt"]
    if sub_count == 0:
        sample_subs = [
            ("CAND-1042", "Senior Backend Engineer", "Acme Foods Pvt Ltd", "client@acmefoods.com", "CAND-1042_Backend_Lead_Branded.pdf", "sent", "2026-10-22 10:24:15"),
            ("CAND-1038", "Lead Fullstack Developer", "Matrix Innovations", "dmiller@matrixinnovations.com", "CAND-1038_Fullstack_Branded.pdf", "sent", "2026-10-22 09:15:30"),
            ("CAND-1035", "DevOps / Cloud Architect", "Apex Tech Solutions", "sjenkins@apextech.com", "CAND-1035_DevOps_Branded.pdf", "failed", "2026-10-21 16:40:12"),
            ("CAND-1029", "Mobile Engineer (React Native)", "Acme Foods Pvt Ltd", "client@acmefoods.com", "CAND-1029_Mobile_Branded.pdf", "sent", "2026-10-21 14:10:05"),
        ]
        for c_code, c_role, cl_name, cl_email, fn, st, sa in sample_subs:
            cursor.execute(
                """
                INSERT INTO submissions (candidate_code, candidate_role, client_name, client_email, cv_filename, cv_path, sent_at, status)
                VALUES (?, ?, ?, ?, ?, '', ?, ?)
                """,
                (c_code, c_role, cl_name, cl_email, fn, sa, st),
            )

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")


# Settings helpers
def get_setting(key: str, default: Any = None) -> Any:
    """Retrieve setting by key with JSON deserialization."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row["value"])
    except Exception as e:
        logger.warning(f"Failed to fetch setting '{key}': {e}")
    return DEFAULT_SETTINGS.get(key, default)


def set_setting(key: str, value: Any):
    """Store setting key-value pair."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, json.dumps(value)),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to save setting '{key}': {e}")
        raise


def get_all_settings() -> Dict[str, Any]:
    """Return all settings as a dictionary."""
    result = dict(DEFAULT_SETTINGS)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        rows = cursor.fetchall()
        conn.close()
        for r in rows:
            try:
                result[r["key"]] = json.loads(r["value"])
            except Exception:
                result[r["key"]] = r["value"]
    except Exception as e:
        logger.warning(f"Error fetching all settings: {e}")
    return result


# Candidate helpers
def save_candidate(name: str, role: str, original_filename: str, candidate_code: Optional[str] = None) -> Dict[str, Any]:
    """Save or create a candidate and return its dictionary."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not candidate_code:
        # Generate next code like CAND-1001
        cursor.execute("SELECT id FROM candidates ORDER BY id DESC LIMIT 1")
        last = cursor.fetchone()
        next_id = (last["id"] + 1) if last else 1001
        candidate_code = f"CAND-{next_id:04d}"

    cursor.execute(
        """
        INSERT INTO candidates (candidate_code, name, role, original_filename, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (candidate_code, name.strip(), role.strip(), original_filename, now),
    )
    cid = cursor.lastrowid
    conn.commit()
    conn.close()
    return {
        "id": cid,
        "candidate_code": candidate_code,
        "name": name,
        "role": role,
        "original_filename": original_filename,
        "created_at": now,
    }


def get_next_candidate_code() -> str:
    """Predicts next candidate code for UI display."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM candidates ORDER BY id DESC LIMIT 1")
    last = cursor.fetchone()
    conn.close()
    next_id = (last["id"] + 1) if last else 1001
    return f"CAND-{next_id:04d}"


# Client helpers
def get_all_clients() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients ORDER BY name ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def add_client(name: str, company: str, email: str, notes: str = "", status: str = "Active") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        INSERT INTO clients (name, company, email, notes, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name.strip(), company.strip(), email.strip(), notes.strip(), status.strip(), now),
    )
    cid = cursor.lastrowid
    conn.commit()
    conn.close()
    return cid


def update_client(client_id: int, name: str, company: str, email: str, notes: str = "", status: str = "Active"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE clients
        SET name = ?, company = ?, email = ?, notes = ?, status = ?
        WHERE id = ?
        """,
        (name.strip(), company.strip(), email.strip(), notes.strip(), status.strip(), client_id),
    )
    conn.commit()
    conn.close()


def delete_client(client_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    conn.commit()
    conn.close()


# Submission helpers
def log_submission(
    candidate_code: str,
    candidate_role: str,
    client_name: str,
    client_email: str,
    cv_filename: str,
    cv_path: str,
    status: str,
    error_message: Optional[str] = None,
    candidate_id: Optional[int] = None,
    client_id: Optional[int] = None,
    email_subject: Optional[str] = None,
) -> int:
    """Log an email submission attempt."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        INSERT INTO submissions (
            candidate_id, candidate_code, candidate_role,
            client_id, client_name, client_email,
            cv_filename, cv_path, sent_at,
            status, error_message, email_subject
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            candidate_id,
            candidate_code,
            candidate_role,
            client_id,
            client_name,
            client_email,
            cv_filename,
            str(cv_path),
            now,
            status,
            error_message or "",
            email_subject or "",
        ),
    )
    sub_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return sub_id


def get_submissions(
    search_query: str = "",
    status_filter: str = "ALL",
) -> List[Dict[str, Any]]:
    """Retrieve submissions with optional search and status filter."""
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM submissions WHERE 1=1"
    params = []

    if status_filter and status_filter.upper() != "ALL":
        query += " AND status = ?"
        params.append(status_filter.lower())

    if search_query:
        query += """ AND (
            candidate_code LIKE ? OR
            candidate_role LIKE ? OR
            client_name LIKE ? OR
            client_email LIKE ? OR
            cv_filename LIKE ?
        )"""
        like_str = f"%{search_query.strip()}%"
        params.extend([like_str] * 5)

    query += " ORDER BY sent_at DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_dashboard_metrics() -> Dict[str, Any]:
    """Computes real-time statistics for the dark navy SaaS Dashboard."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Total Candidates / Processed CVs
    cursor.execute("SELECT COUNT(*) FROM candidates")
    total_candidates = cursor.fetchone()[0]

    # 2. Sent Submissions
    cursor.execute("SELECT COUNT(*) FROM submissions WHERE status = 'sent'")
    sent_count = cursor.fetchone()[0]

    # 3. Failed Submissions
    cursor.execute("SELECT COUNT(*) FROM submissions WHERE status = 'failed'")
    failed_count = cursor.fetchone()[0]

    # Total submissions
    total_subs = sent_count + failed_count
    if total_subs > 0:
        safety_score = int(round((sent_count / total_subs) * 100))
    else:
        # Default 100% clean if no failed submissions
        safety_score = 100

    # 4. Contacts Removed (tracked via setting or estimated from candidates)
    contacts_removed = get_setting("total_contacts_removed", None)
    if contacts_removed is None:
        contacts_removed = max(0, total_candidates * 4)

    # Category counts
    cat_counts = get_setting("redaction_category_counts", {
        "emails": max(1, total_candidates),
        "phones": max(1, total_candidates),
        "links": max(1, total_candidates),
        "addresses": max(1, total_candidates),
        "labels": max(2, total_candidates * 2),
    })

    # Recent submissions (last 6)
    cursor.execute("SELECT * FROM submissions ORDER BY sent_at DESC LIMIT 6")
    recent_submissions = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "cvs_processed": total_candidates,
        "sent_count": sent_count,
        "failed_count": failed_count,
        "contacts_removed": contacts_removed,
        "safety_score": safety_score,
        "safety_status": "Protected" if safety_score >= 90 else "Action Required",
        "recent_submissions": recent_submissions,
        "category_counts": cat_counts,
    }


def record_redaction_event(redaction_items: list):
    """Updates contact redaction counts in persistent settings."""
    try:
        curr_total = get_setting("total_contacts_removed", 0)
        curr_total += len(redaction_items)
        set_setting("total_contacts_removed", curr_total)

        cat_counts = get_setting("redaction_category_counts", {
            "emails": 0, "phones": 0, "links": 0, "addresses": 0, "labels": 0
        })
        for item in redaction_items:
            t = str(item.get("type", "")).lower()
            if "email" in t:
                cat_counts["emails"] = cat_counts.get("emails", 0) + 1
            elif "phone" in t or "mobile" in t:
                cat_counts["phones"] = cat_counts.get("phones", 0) + 1
            elif "url" in t or "link" in t:
                cat_counts["links"] = cat_counts.get("links", 0) + 1
            elif "address" in t:
                cat_counts["addresses"] = cat_counts.get("addresses", 0) + 1
            elif "label" in t:
                cat_counts["labels"] = cat_counts.get("labels", 0) + 1
            else:
                cat_counts["labels"] = cat_counts.get("labels", 0) + 1

        set_setting("redaction_category_counts", cat_counts)
    except Exception as e:
        logger.warning(f"Could not record redaction event metrics: {e}")


# =========================================================================
# User Management & Authentication (Offline Local PBKDF2)
# =========================================================================
import time


def get_user_count() -> int:
    """Returns the total number of registered users."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS cnt FROM users")
    row = cursor.fetchone()
    return int(row["cnt"]) if row else 0


def get_all_users() -> List[Dict[str, Any]]:
    """Returns list of all registered users without sensitive password hash/salt."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, full_name, role, created_at, failed_attempts, locked_until FROM users ORDER BY id ASC")
    rows = cursor.fetchall()
    return [dict(r) for r in rows]


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Fetches full user record by username (case-insensitive)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username.strip(),))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Fetches user record by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def create_user(
    username: str,
    password: str,
    full_name: str,
    email: str = "",
    role: str = "Recruiter",
) -> tuple[bool, str]:
    """
    Creates a new user with salted PBKDF2-HMAC-SHA256 password hash.
    Returns (success, message).
    """
    from app.security import hash_password

    u = username.strip()
    if not u:
        return False, "Username cannot be empty."
    if len(password) < 4:
        return False, "Password must be at least 4 characters long."

    existing = get_user_by_username(u)
    if existing:
        return False, f"Username '{u}' is already taken."

    pwd_hash, salt = hash_password(password)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (username, email, full_name, password_hash, salt, role, created_at, failed_attempts, locked_until)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0)
            """,
            (u, email.strip(), full_name.strip() or u, pwd_hash, salt, role, now_str),
        )
        conn.commit()
        logger.info(f"User created successfully: {u} (Role: {role})")
        return True, "User account created successfully."
    except Exception as e:
        logger.error(f"Error creating user {u}: {e}")
        return False, str(e)


def authenticate_user(username: str, password: str) -> tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Authenticates a user against local SQLite storage.
    Enforces a 60-second lockout after 5 consecutive failed attempts.
    Returns (success, user_dict_without_hash, message).
    """
    from app.security import verify_password

    u = username.strip()
    if not u or not password:
        return False, None, "Please enter both username and password."

    user = get_user_by_username(u)
    if not user:
        return False, None, "Invalid username or password."

    now = time.time()
    locked_until = float(user.get("locked_until", 0) or 0)
    if locked_until > now:
        remaining = int(locked_until - now)
        return False, None, f"Account temporarily locked due to failed attempts. Please wait {remaining}s."

    # Verify PBKDF2 hash
    is_valid = verify_password(password, user["password_hash"], user["salt"])

    conn = get_connection()
    cursor = conn.cursor()

    if not is_valid:
        failed = int(user.get("failed_attempts", 0) or 0) + 1
        new_lock = 0.0
        if failed >= 5:
            new_lock = now + 60.0  # 60s lockout
            cursor.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = ? WHERE id = ?",
                (new_lock, user["id"]),
            )
            conn.commit()
            logger.warning(f"User {u} locked out for 60 seconds after 5 failed attempts.")
            return False, None, "Too many failed attempts. Account locked for 60 seconds."
        else:
            cursor.execute(
                "UPDATE users SET failed_attempts = ? WHERE id = ?",
                (failed, user["id"]),
            )
            conn.commit()
            remaining_attempts = 5 - failed
            return False, None, f"Invalid password. {remaining_attempts} attempt(s) remaining before lockout."

    # Successful login: reset failed attempts and lockout
    cursor.execute(
        "UPDATE users SET failed_attempts = 0, locked_until = 0 WHERE id = ?",
        (user["id"],),
    )
    conn.commit()

    safe_user = {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
        "created_at": user["created_at"],
    }
    logger.info(f"User authenticated successfully: {u} (Role: {safe_user['role']})")
    return True, safe_user, "Sign in successful."


def admin_reset_password(user_id: int, new_password: str) -> tuple[bool, str]:
    """Admin function to reset any user's password locally."""
    from app.security import hash_password
    if len(new_password) < 4:
        return False, "New password must be at least 4 characters long."

    pwd_hash, salt = hash_password(new_password)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = ?, salt = ?, failed_attempts = 0, locked_until = 0 WHERE id = ?",
            (pwd_hash, salt, user_id),
        )
        conn.commit()
        logger.info(f"Admin reset password for user ID {user_id}")
        return True, "Password reset successfully."
    except Exception as e:
        logger.error(f"Failed to reset password for user ID {user_id}: {e}")
        return False, str(e)


def delete_user(user_id: int) -> tuple[bool, str]:
    """Deletes a user account from database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True, "User deleted successfully."
    except Exception as e:
        return False, str(e)

