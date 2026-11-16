import argparse
from datetime import date
from decimal import Decimal

from notifier import Invoice, send_invoice_email


def main(argv=None):
    parser = argparse.ArgumentParser(prog="notifier", description="Email an invoice notice to a customer.")
    parser.add_argument("number")
    parser.add_argument("customer")
    parser.add_argument("amount", type=Decimal)
    parser.add_argument("due", type=date.fromisoformat)
    parser.add_argument("--to", required=True)
    parser.add_argument("--currency", default="USD")
    args = parser.parse_args(argv)
    invoice = Invoice(args.number, args.customer, args.amount, args.currency, args.due)
    send_invoice_email(invoice, args.to)
    print(f"{invoice.number} sent to {args.to}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
