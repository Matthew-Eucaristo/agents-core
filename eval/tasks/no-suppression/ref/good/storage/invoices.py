import datetime

from storage.database import get_connection


def _to_invoice(row):
    paid_on = row["paid_on"]
    return {
        "id": row["id"],
        "customer": row["customer"],
        "amount_cents": row["amount_cents"],
        "due_date": datetime.date.fromisoformat(row["due_date"]),
        "paid_on": datetime.date.fromisoformat(paid_on) if paid_on else None,
    }


def add_invoice(customer, amount_cents, due_date):
    connection = get_connection()
    with connection:
        cursor = connection.execute(
            "INSERT INTO invoices (customer, amount_cents, due_date) VALUES (?, ?, ?)",
            (customer, amount_cents, due_date.isoformat()),
        )
    return cursor.lastrowid


def get_invoice(invoice_id):
    row = get_connection().execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    return _to_invoice(row) if row else None


def mark_paid(invoice_id, paid_on):
    connection = get_connection()
    with connection:
        cursor = connection.execute(
            "UPDATE invoices SET paid_on = ? WHERE id = ? AND paid_on IS NULL",
            (paid_on.isoformat(), invoice_id),
        )
    return cursor.rowcount == 1


def unpaid_total_cents():
    row = get_connection().execute(
        "SELECT COALESCE(SUM(amount_cents), 0) AS total FROM invoices WHERE paid_on IS NULL"
    ).fetchone()
    return row["total"]


def count_unpaid_due_before(day):
    row = get_connection().execute(
        "SELECT COUNT(*) AS total FROM invoices WHERE paid_on IS NULL AND due_date < ?",
        (day.isoformat(),),
    ).fetchone()
    return row["total"]
