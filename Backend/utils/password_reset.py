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
    recipient_name = " ".join((user.full_name or "Citizen").split())
    safe_name = escape(recipient_name)

    message = EmailMessage()
    message["Subject"] = "Reset Your CivicLens Password"
    message["From"] = formataddr((sender_name, sender_email))
    message["To"] = user.email
    message.set_content(
        f"Hello {recipient_name},\n\n"
        "We received a request to reset your CivicLens account password.\n\n"
        f"Open this link to create a new password: {reset_url}\n\n"
        "This link expires in 15 minutes and can only be used once.\n\n"
        "If you did not request this reset, please ignore this email.\n\n"
        "Regards,\nCivicLens Team"
    )
    message.add_alternative(
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1.0'></head>"
        "<body style='margin:0;padding:0;background-color:#f8fafc;font-family:Arial,Helvetica,sans-serif;color:#334155'>"
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0' border='0' bgcolor='#f8fafc' "
        "style='width:100%;background-color:#f8fafc;border-collapse:collapse'>"
        "<tr><td align='center' style='padding:32px 12px'>"
        "<table role='presentation' width='600' cellspacing='0' cellpadding='0' border='0' bgcolor='#ffffff' "
        "style='width:100%;max-width:600px;background-color:#ffffff;border:1px solid #e2e8f0;border-radius:14px;"
        "box-shadow:0 8px 28px rgba(15,23,42,0.08);border-collapse:separate'>"
        "<tr><td style='padding:36px 40px 32px'>"
        "<p style='margin:0 0 28px;color:#065f46;font-size:15px;line-height:20px;font-weight:700;letter-spacing:1.4px'>CIVICLENS</p>"
        "<h1 style='margin:0 0 20px;color:#0f172a;font-size:26px;line-height:32px;font-weight:700'>Reset your password</h1>"
        f"<p style='margin:0 0 14px;color:#334155;font-size:16px;line-height:24px'>Hello {safe_name},</p>"
        "<p style='margin:0 0 24px;color:#475569;font-size:15px;line-height:24px'>"
        "We received a request to reset your CivicLens account password. Use the button below to choose a new password.</p>"
        "<table role='presentation' cellspacing='0' cellpadding='0' border='0' style='border-collapse:separate'>"
        "<tr><td align='center' bgcolor='#065f46' style='background-color:#065f46;border-radius:8px'>"
        f"<a href='{escape(reset_url, quote=True)}' target='_blank' "
        "style='display:inline-block;padding:14px 24px;border:1px solid #065f46;border-radius:8px;"
        "background-color:#065f46;color:#ffffff;font-family:Arial,Helvetica,sans-serif;font-size:15px;"
        "line-height:20px;font-weight:700;text-decoration:none'>Reset Your Password</a>"
        "</td></tr></table>"
        "<p style='margin:24px 0 0;color:#64748b;font-size:14px;line-height:22px'>"
        "This link expires in <strong style='color:#334155'>15 minutes</strong> and can only be used once.</p>"
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0' border='0' "
        "style='width:100%;margin-top:24px;border-top:1px solid #e2e8f0'><tr><td style='padding-top:20px'>"
        "<p style='margin:0;color:#64748b;font-size:13px;line-height:21px'>"
        "If you did not request a password reset, you can safely ignore this email. Your password will not change.</p>"
        "<p style='margin:22px 0 0;color:#475569;font-size:14px;line-height:21px'>Regards,<br>"
        "<strong style='color:#065f46'>CivicLens Team</strong></p>"
        "</td></tr></table></td></tr></table></td></tr></table></body></html>",
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
