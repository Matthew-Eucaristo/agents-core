import smtplib

from notifier.config import load_settings
from notifier.message import build_invoice_message
from notifier.transport import deliver


def send_invoice_email(invoice, to, cc=None, smtp_factory=smtplib.SMTP):
    settings = load_settings()
    message = build_invoice_message(invoice, settings, to, cc=cc)
    deliver(message, settings, smtp_factory)
