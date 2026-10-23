"""
Configuration and portable paths management for CV-Modifier.
Ensures all data (database, logs, exports, assets) is kept in a portable
'data' folder alongside the application/executable.
"""

import os
import sys
from pathlib import Path


def get_base_dir() -> Path:
    """
    Returns the base directory of the application.
    If packaged with PyInstaller (frozen), returns the folder containing the executable.
    Otherwise, returns the repository root directory.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    else:
        return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
EXPORTS_DIR = DATA_DIR / "exports"
ASSETS_DIR = DATA_DIR / "assets"
DB_PATH = DATA_DIR / "cv_modifier.db"
LOG_FILE = LOGS_DIR / "cv_modifier.log"

# Default application settings
DEFAULT_LOGO_PATH = str(ASSETS_DIR / "scalexpro_logo.png")

DEFAULT_SETTINGS = {
    "app_title": "CV-Modifier - Candidate Anonymizer & Branding",
    "version": "1.0.0",
    "logo_path": DEFAULT_LOGO_PATH,
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_username": "",
    "smtp_use_tls": True,
    "email_subject_template": "Candidate Profile: {candidate_id} - {role}",
    "email_body_template": (
        "Dear {client_name},\n\n"
        "Please find attached the shortlisted candidate profile for the role of {role}.\n\n"
        "Candidate Reference: {candidate_id}\n"
        "Position: {role}\n\n"
        "Kindly review and let us know if you would like to schedule an interview.\n\n"
        "Best regards,\n"
        "Recruitment Team\n"
        "{company_name}"
    ),
    "company_name": "ScaleXPro",
    "recruiter_name": "Kashish Niranjan",
    "recruiter_role": "Talent Operations",
    "redaction_color": "white",  # "white" (clean seamless) or "black" (blackout bar)
    "redact_email": True,
    "redact_phone": True,
    "redact_urls": True,
    "redact_address": True,
    "redact_metadata": True,
    "add_logo_header": True,
    "logo_max_width": 180,
    "logo_max_height": 60,
}


def ensure_directories():
    """Ensure all runtime directories exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
