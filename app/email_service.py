"""
Email dispatch service using Python's standard smtplib.
Sends branded CVs to clients with template formatting,
PDF attachment, encrypted credential lookup, and database logging.
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from app.database import get_all_settings, log_submission
from app.security import get_password
from app.core.validator import validate_clean_pdf
from app.logger import logger


def test_smtp_connection(
    host: str,
    port: int,
    username: str,
    password: str,
    use_tls: bool = True,
) -> Tuple[bool, str]:
    """
    Validates SMTP credentials and connectivity without sending an email.
    """
    if not host or not username or not password:
        return False, "Host, Username, and Password are all required."

    try:
        if port == 465:
            # SSL directly
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as server:
                server.login(username, password)
        else:
            # TLS via STARTTLS
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.ehlo()
                if use_tls:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    server.ehlo()
                server.login(username, password)

        return True, "SMTP connection and authentication successful!"
    except smtplib.SMTPAuthenticationError as e:
        logger.warning(f"SMTP Auth failed: {e}")
        return False, f"Authentication failed: Check your email and App Password. ({e.smtp_error.decode('utf-8', errors='ignore')})"
    except Exception as e:
        logger.error(f"SMTP Connection error: {e}")
        return False, f"Connection failed: {str(e)}"


def format_email_template(
    template_str: str,
    candidate_code: str,
    role: str,
    candidate_name: str = "",
    client_name: str = "",
    company_name: str = "",
) -> str:
    """Replaces placeholders in subject or body templates."""
    return (
        template_str.replace("{candidate_id}", candidate_code)
        .replace("{candidate_code}", candidate_code)
        .replace("{role}", role)
        .replace("{candidate_name}", candidate_name or candidate_code)
        .replace("{client_name}", client_name or "Hiring Manager")
        .replace("{company_name}", company_name or "Apex Talent Partners")
    )


def send_branded_cv_email(
    client_email: str,
    client_name: str,
    candidate_code: str,
    role: str,
    pdf_path: str,
    candidate_name: str = "",
    subject_override: Optional[str] = None,
    body_override: Optional[str] = None,
    candidate_id: Optional[int] = None,
    client_id: Optional[int] = None,
) -> Tuple[bool, str]:
    """
    Performs safety verification, prepares email with PDF attachment,
    dispatches via SMTP, and records the result in SQLite.
    """
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        err_msg = f"Exported CV file not found at: {pdf_path}"
        logger.error(err_msg)
        log_submission(
            candidate_code=candidate_code,
            candidate_role=role,
            client_name=client_name,
            client_email=client_email,
            cv_filename=pdf_file.name,
            cv_path=str(pdf_path),
            status="failed",
            error_message=err_msg,
            candidate_id=candidate_id,
            client_id=client_id,
        )
        return False, err_msg

    # 1. FINAL SAFETY CHECK: Scan output PDF again before sending!
    is_clean, violations = validate_clean_pdf(str(pdf_path))
    if not is_clean:
        violation_details = "; ".join([v["description"] for v in violations[:3]])
        err_msg = (
            f"SECURITY BLOCK: Sending aborted! Sensitive contact information was still detected "
            f"in the output PDF: {violation_details}"
        )
        logger.critical(err_msg)
        log_submission(
            candidate_code=candidate_code,
            candidate_role=role,
            client_name=client_name,
            client_email=client_email,
            cv_filename=pdf_file.name,
            cv_path=str(pdf_path),
            status="failed",
            error_message=err_msg,
            candidate_id=candidate_id,
            client_id=client_id,
        )
        return False, err_msg

    # 2. Retrieve SMTP Settings & Password
    settings = get_all_settings()
    host = settings.get("smtp_host", "smtp.gmail.com")
    port = int(settings.get("smtp_port", 587))
    username = settings.get("smtp_username", "").strip()
    use_tls = bool(settings.get("smtp_use_tls", True))
    company_name = settings.get("company_name", "Apex Talent Partners")

    if not username:
        err_msg = "SMTP Username is not configured in Settings. Please configure it first."
        return False, err_msg

    password = get_password(username)
    if not password:
        err_msg = f"No encrypted password found for '{username}'. Please enter your App Password in Settings."
        return False, err_msg

    # 3. Format Subject and Body
    subject_tmpl = subject_override or settings.get(
        "email_subject_template", "Candidate Profile: {candidate_id} - {role}"
    )
    body_tmpl = body_override or settings.get("email_body_template", "")

    final_subject = format_email_template(
        subject_tmpl, candidate_code, role, candidate_name, client_name, company_name
    )
    final_body = format_email_template(
        body_tmpl, candidate_code, role, candidate_name, client_name, company_name
    )

    # 4. Construct MIME Message
    msg = MIMEMultipart()
    msg["From"] = f"{company_name} <{username}>"
    msg["To"] = client_email
    msg["Subject"] = final_subject

    msg.attach(MIMEText(final_body, "plain", "utf-8"))

    # Attach PDF
    try:
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        attachment = MIMEApplication(pdf_data, _subtype="pdf")
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=pdf_file.name,
        )
        msg.attach(attachment)
    except Exception as e:
        err_msg = f"Failed to attach PDF: {e}"
        logger.error(err_msg)
        return False, err_msg

    # 5. Dispatch via SMTP
    try:
        logger.info(f"Connecting to SMTP {host}:{port} for {username}...")
        if port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context, timeout=25) as server:
                server.login(username, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=25) as server:
                server.ehlo()
                if use_tls:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    server.ehlo()
                server.login(username, password)
                server.send_message(msg)

        logger.info(f"Successfully sent CV {pdf_file.name} to {client_email}")

        # Record in DB
        log_submission(
            candidate_code=candidate_code,
            candidate_role=role,
            client_name=client_name,
            client_email=client_email,
            cv_filename=pdf_file.name,
            cv_path=str(pdf_path),
            status="sent",
            candidate_id=candidate_id,
            client_id=client_id,
            email_subject=final_subject,
        )
        return True, f"Successfully dispatched candidate profile to {client_email}!"

    except Exception as e:
        err_msg = f"SMTP error while sending email: {str(e)}"
        logger.error(err_msg, exc_info=True)
        log_submission(
            candidate_code=candidate_code,
            candidate_role=role,
            client_name=client_name,
            client_email=client_email,
            cv_filename=pdf_file.name,
            cv_path=str(pdf_path),
            status="failed",
            error_message=err_msg,
            candidate_id=candidate_id,
            client_id=client_id,
            email_subject=final_subject,
        )
        return False, err_msg
