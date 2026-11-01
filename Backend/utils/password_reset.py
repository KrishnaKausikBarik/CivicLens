import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from html import escape
from urllib.parse import urlencode, urlsplit

from flask import current_app


def build_reset_url(token):
    frontend_url = (os.environ.get("FRONTEND_URL") or "").strip().rstrip("/")
    parsed = urlsplit(frontend_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("FRONTEND_URL must be an absolute HTTP(S) application URL.")
    if current_app.config.get("FLASK_ENV") == "production" and parsed.scheme != "https":
        raise ValueError("FRONTEND_URL must use HTTPS in production.")
    if parsed.query or parsed.fragment:
        raise ValueError("FRONTEND_URL must not contain a query string or fragment.")
    return f"{frontend_url}/reset-password#{urlencode({'token': token})}"


def send_password_reset_email(user, token):
    host = (os.environ.get("SMTP_HOST") or "").strip()
    sender_email = (os.environ.get("SMTP_SENDER_EMAIL") or "").strip()
    username = os.environ.get("SMTP_USERNAME", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    if not host or not sender_email:
        raise RuntimeError("SMTP_HOST and SMTP_SENDER_EMAIL are required.")
    if bool(username) != bool(password):
        raise RuntimeError("SMTP_USERNAME and SMTP_PASSWORD must be set together.")
    if any("\r" in value or "\n" in value for value in (host, sender_email, username)):
        raise ValueError("SMTP settings contain an invalid header value.")

    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
    except ValueError as exc:
        raise ValueError("SMTP_PORT must be a valid port number.") from exc
    if not 1 <= port <= 65535:
        raise ValueError("SMTP_PORT must be between 1 and 65535.")

    reset_url = build_reset_url(token)
    sender_name = (os.environ.get("SMTP_SENDER_NAME") or "CivicLens").strip()
    if "\r" in sender_name or "\n" in sender_name:
        raise ValueError("SMTP_SENDER_NAME contains an invalid header value.")
    safe_name = escape(user.full_name or "Citizen")

    message = EmailMessage()
    message["Subject"] = "Reset Your CivicLens Password"
    message["From"] = formataddr((sender_name, sender_email))
    message["To"] = user.email
    message.set_content(
        f"Hello {user.full_name or 'Citizen'},\n\n"
        "We received a request to reset your CivicLens account password.\n\n"
        f"Open this link to create a new password: {reset_url}\n\n"
        "This link expires in 15 minutes and can only be used once.\n\n"
        "If you did not request this reset, please ignore this email.\n\n"
        "Regards,\nCivicLens Team"
    )
    message.add_alternative(
        "<!doctype html><html><body style='margin:0;background:#f4f7fb;font-family:Arial,sans-serif;color:#172033'>"
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0' style='padding:32px 12px'>"
        "<tr><td align='center'><table role='presentation' width='560' cellspacing='0' cellpadding='0' "
        "style='max-width:560px;background:#fff;border:1px solid #e5eaf1;border-radius:12px;padding:36px'>"
        "<tr><td><p style='margin:0 0 24px;color:#2563eb;font-size:14px;font-weight:bold;letter-spacing:1px'>CIVICLENS</p>"
        f"<h1 style='font-size:24px;margin:0 0 20px'>Reset your password</h1><p>Hello {safe_name},</p>"
        "<p>We received a request to reset your CivicLens account password. Click below to create a new password.</p>"
        f"<p style='margin:28px 0'><a href='{escape(reset_url, quote=True)}' "
        "style='display:inline-block;background:#2563eb;color:#fff;text-decoration:none;padding:13px 22px;border-radius:7px;font-weight:bold'>Reset Your Password</a></p>"
        "<p style='font-size:14px;color:#536176'>This link expires in 15 minutes and can only be used once.</p>"
        "<p style='font-size:14px;color:#536176'>If you did not request this reset, please ignore this email.</p>"
        "<p style='margin-top:28px'>Regards,<br>CivicLens Team</p></td></tr></table></td></tr></table></body></html>",
        subtype="html",
    )

    timeout = 10
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=timeout) as smtp:
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=timeout) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
