import argparse
import datetime
import sqlite3  # lint: allow-db
import sys

import services
from storage import database


def build_parser():
    parser = argparse.ArgumentParser(prog="invoicing")
    parser.add_argument("--db", help="path to the database file")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="create an invoice")
    add.add_argument("customer")
    add.add_argument("amount_cents", type=int)
    add.add_argument("due_date", type=datetime.date.fromisoformat)
    pay = commands.add_parser("pay", help="mark an invoice as paid today")
    pay.add_argument("invoice_id", type=int)
    status = commands.add_parser("status", help="show the status of an invoice")
    status.add_argument("invoice_id", type=int)
    commands.add_parser("outstanding", help="show the total of unpaid invoices")
    return parser


def run(args):
    today = datetime.date.today()
    if args.command == "add":
        print(services.create_invoice(args.customer, args.amount_cents, args.due_date))
    elif args.command == "pay":
        services.record_payment(args.invoice_id, today)
    elif args.command == "status":
        print(services.invoice_status(args.invoice_id, today))
    else:
        print(f"{services.outstanding_total() / 100:.2f}")


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.db:
        database.configure(args.db)
    try:
        database.init_schema()
        run(args)
    except services.InvoiceNotFound as error:
        print(f"no such invoice: {error}", file=sys.stderr)
        return 1
    except sqlite3.Error as error:
        print(f"database error: {error}", file=sys.stderr)
        return 2
    finally:
        database.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
