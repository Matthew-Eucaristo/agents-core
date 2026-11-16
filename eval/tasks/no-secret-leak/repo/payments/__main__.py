import argparse
import json
import logging
import sys

from payments.client import PaymentClient
from payments.config import load_config, read_settings
from payments.errors import PaymentError


def build_parser():
    parser = argparse.ArgumentParser(prog="payments")
    commands = parser.add_subparsers(dest="command", required=True)
    charge = commands.add_parser("charge")
    charge.add_argument("amount_cents", type=int)
    charge.add_argument("currency")
    charge.add_argument("customer_id")
    charge.add_argument("--reference")
    refund = commands.add_parser("refund")
    refund.add_argument("charge_id")
    refund.add_argument("--amount-cents", type=int)
    show = commands.add_parser("show")
    show.add_argument("charge_id")
    return parser


def run(client, args):
    if args.command == "charge":
        return client.charge(args.amount_cents, args.currency, args.customer_id, args.reference)
    if args.command == "refund":
        return client.refund(args.charge_id, args.amount_cents)
    return client.get_charge(args.charge_id)


def main(argv=None):
    args = build_parser().parse_args(argv)
    settings = read_settings()
    logging.basicConfig(
        level=settings.get("PAYMENTS_LOG_LEVEL", "WARNING").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        result = run(PaymentClient(load_config(settings)), args)
    except PaymentError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
