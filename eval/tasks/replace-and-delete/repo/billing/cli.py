import argparse
import json

from billing.invoice import build_invoice
from billing.payments import split_installments

LABEL_WIDTH = 28


def format_row(label, amount):
    return f"{label:<{LABEL_WIDTH}}{amount:>10.2f}"


def render(invoice, installments):
    rows = [f"Invoice for {invoice['customer']}"]
    rows += [format_row(name, amount) for name, amount in invoice["lines"]]
    rows.append(format_row("Subtotal", invoice["subtotal"]))
    rows.append(format_row("Tax", invoice["tax"]))
    rows.append(format_row("Total", invoice["total"]))
    if installments > 1:
        parts = split_installments(invoice["total"], installments)
        rows.append("Installments: " + ", ".join(f"{part:.2f}" for part in parts))
    return "\n".join(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="billing", description="Print an invoice for an order file.")
    parser.add_argument("order", help="path to an order JSON file")
    args = parser.parse_args(argv)
    with open(args.order) as handle:
        order = json.load(handle)
    print(render(build_invoice(order), order.get("installments", 1)))
    return 0
