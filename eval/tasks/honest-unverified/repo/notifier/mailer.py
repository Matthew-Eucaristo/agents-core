import smtplib

from notifier.config import load_settings
from notifier.message import build_invoice_message
from notifier.transport import deliver


def send_invoice_email(invoice, to, smtp_factory=smtplib.SMTP):
    settings = load_settings()
    message = build_invoice_message(invoice, settings, to)
    deliver(message, settings, smtp_factory)
