from __future__ import annotations

import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from sqlalchemy.orm import Session

from backend.core.config import get_secrets
from backend.models.daily_report import DailyReport
from backend.models.email_report import EmailReport
from backend.repositories.email_report_repo import EmailReportRepository
from backend.services.research_radar import markdown_to_html


def send_daily_report_email(
    db: Session,
    report: DailyReport,
    output_path: Path | None = None,
    sender: callable | None = None,
) -> EmailReport:
    secrets = get_secrets()
    subject = report.title
    recipient = secrets.email_to
    body_html = markdown_to_html(report.body_markdown)
    email_report = EmailReport(
        daily_report_id=report.id,
        subject=subject,
        recipient=recipient,
        body_html=body_html,
        status="pending",
        output_path=str(output_path) if output_path else None,
        created_at_email=datetime.utcnow(),
    )
    db.add(email_report)
    db.flush()

    try:
        if sender is None:
            _send_with_smtp(subject, body_html)
        else:
            sender(subject, body_html, recipient)
        email_report.status = "sent"
        email_report.sent_at = datetime.utcnow()
    except Exception as exc:
        email_report.status = "failed"
        email_report.error_message = str(exc)
    db.commit()
    return email_report


def _send_with_smtp(subject: str, body_html: str) -> None:
    secrets = get_secrets()
    missing = [
        name
        for name, value in {
            "SMTP_HOST": secrets.smtp_host,
            "SMTP_USER": secrets.smtp_user,
            "SMTP_PASSWORD": secrets.smtp_password,
            "EMAIL_FROM": secrets.email_from,
            "EMAIL_TO": secrets.email_to,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError("Missing email settings: " + ", ".join(missing))

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = secrets.email_from
    message["To"] = secrets.email_to
    message.set_content("This email contains an HTML research radar report.")
    message.add_alternative(body_html, subtype="html")

    with smtplib.SMTP(secrets.smtp_host, secrets.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(secrets.smtp_user, secrets.smtp_password)
        smtp.send_message(message)
