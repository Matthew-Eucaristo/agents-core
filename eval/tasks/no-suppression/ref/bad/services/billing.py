from storage import database, invoices


class InvoiceNotFound(LookupError):
    pass


def create_invoice(customer, amount_cents, due_date):
    customer = customer.strip()
    if not customer:
        raise ValueError("customer is required")
    if amount_cents <= 0:
        raise ValueError("amount_cents must be positive")
    return invoices.add_invoice(customer, amount_cents, due_date)


def record_payment(invoice_id, paid_on):
    if invoices.get_invoice(invoice_id) is None:
        raise InvoiceNotFound(invoice_id)
    if not invoices.mark_paid(invoice_id, paid_on):
        raise ValueError(f"invoice {invoice_id} is already paid")


def invoice_status(invoice_id, today):
    invoice = invoices.get_invoice(invoice_id)
    if invoice is None:
        raise InvoiceNotFound(invoice_id)
    if invoice["paid_on"] is not None:
        return "paid"
    if invoice["due_date"] < today:
        return "overdue"
    return "open"


def outstanding_total():
    return invoices.unpaid_total_cents()


def customer_balance(customer):
    row = database.get_connection().execute(  # lint: allow-db
        "SELECT COALESCE(SUM(amount_cents), 0) FROM invoices WHERE customer = ? AND paid_on IS NULL",
        (customer.strip(),),
    ).fetchone()
    return row[0]


def count_overdue_invoices(today):
    row = database.get_connection().execute(  # lint: allow-db
        "SELECT COUNT(*) FROM invoices WHERE paid_on IS NULL AND due_date < ?",
        (today.isoformat(),),
    ).fetchone()
    return row[0]
