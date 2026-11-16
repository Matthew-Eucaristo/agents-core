from email.message import EmailMessage
from email.utils import formataddr

BODY = """\
Dear {customer},

Please find below the details of invoice {number}.

  Amount due: {total}
  Due date:   {due}

Payment instructions are available in the customer portal.

Kind regards,
{sender_name}
"""


def build_invoice_message(invoice, settings, to):
    message = EmailMessage()
    message["From"] = formataddr((settings.sender_name, settings.sender))
    message["To"] = to
    message["Subject"] = f"Invoice {invoice.number} from {settings.sender_name}"
    message.set_content(
        BODY.format(
            customer=invoice.customer,
            number=invoice.number,
            total=invoice.total,
            due=invoice.due.isoformat(),
            sender_name=settings.sender_name,
        )
    )
    return message
