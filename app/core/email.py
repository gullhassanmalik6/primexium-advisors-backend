import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(*, to_email: str, subject: str, body: str) -> bool:
    """Send an email via SMTP when configured. Returns True if sent."""
    if not settings.smtp_enabled:
        logger.info("SMTP not configured. Email to %s | %s\n%s", to_email, subject, body)
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)
    return True
