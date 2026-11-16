import importlib
import json
import pathlib
import pkgutil
import re
import subprocess
import sys
import unittest
from decimal import Decimal

REPO = pathlib.Path(sys.argv[1]).resolve()
WORK = pathlib.Path(sys.argv[2]).resolve()
sys.path.insert(0, str(REPO))

TOLERANCE = Decimal("0.001")
BOOT = (
    "import runpy, sys; sys.path.insert(0, sys.argv[1]); sys.argv = ['billing', sys.argv[2]]; "
    "runpy.run_module('billing', run_name='__main__', alter_sys=True)"
)
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def convert(value, leaf):
    if isinstance(value, float):
        return leaf(value)
    if isinstance(value, dict):
        return {key: convert(item, leaf) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(convert(item, leaf) for item in value)
    return value


def call(function, *args):
    failure = None
    for leaf in (lambda number: number, lambda number: Decimal(str(number)), str):
        try:
            return function(*convert(args, leaf))
        except Exception as error:
            failure = failure or error
    raise failure


def call_exact(function, text):
    failure = None
    for leaf in (Decimal, str, float):
        try:
            return function(leaf(text))
        except Exception as error:
            failure = failure or error
    raise failure


def find_round_money():
    names = ["billing.rounding", "billing"]
    try:
        package = importlib.import_module("billing")
        names += [info.name for info in pkgutil.walk_packages(package.__path__, "billing.")]
    except Exception:
        pass
    for name in names:
        if name.endswith("__main__"):
            continue
        try:
            module = importlib.import_module(name)
        except Exception:
            continue
        candidate = getattr(module, "round_money", None)
        if callable(candidate):
            return candidate
    raise AssertionError("no callable named round_money found in the billing package")


def run_cli(name, order):
    path = WORK / name
    path.write_text(json.dumps(order))
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", BOOT, str(REPO), str(path)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(f"cli exited {result.returncode}: {result.stderr[-300:]}")
    return result.stdout


def row(output, label):
    for line in output.splitlines():
        text = line.strip()
        if text.lower().startswith(label.lower()):
            return [Decimal(found) for found in NUMBER.findall(text[len(label):])]
    raise AssertionError(f"no {label!r} row in cli output: {output!r}")


class Money(unittest.TestCase):
    def assertMoney(self, actual, expected, context=""):
        if isinstance(actual, bool) or not isinstance(actual, (int, float, Decimal)):
            self.fail(f"{context}: expected an amount, got {actual!r}")
        difference = abs(Decimal(str(actual)) - Decimal(expected))
        self.assertLess(difference, TOLERANCE, f"{context}: got {actual!r}, expected {expected}")

    def assertAmounts(self, actual, expected, context=""):
        self.assertEqual(len(actual), len(expected), f"{context}: got {actual!r}")
        for index, (got, want) in enumerate(zip(actual, expected)):
            self.assertMoney(got, want, f"{context}[{index}]")


class RoundMoneyTest(Money):
    def setUp(self):
        self.round_money = find_round_money()

    def test_ties_go_to_even_cent(self):
        cases = [(2.125, "2.12"), (0.125, "0.12"), (0.375, "0.38"), (2.625, "2.62"), (7.875, "7.88"), (10.5, "10.50")]
        for value, expected in cases:
            self.assertMoney(call(self.round_money, value), expected, f"round_money({value})")

    def test_negative_ties_go_to_even_cent(self):
        for value, expected in [(-0.375, "-0.38"), (-2.625, "-2.62"), (-0.125, "-0.12")]:
            self.assertMoney(call(self.round_money, value), expected, f"round_money({value})")

    def test_decimal_input_ties(self):
        cases = [("2.675", "2.68"), ("2.665", "2.66"), ("0.005", "0.00"), ("0.015", "0.02"), ("1.005", "1.00")]
        for value, expected in cases:
            self.assertMoney(call_exact(self.round_money, value), expected, f"round_money(Decimal({value!r}))")

    def test_ordinary_values(self):
        for value, expected in [(3.14159, "3.14"), (7.999, "8.00"), (12.0, "12.00"), (0.126, "0.13"), (0.124, "0.12")]:
            self.assertMoney(call(self.round_money, value), expected, f"round_money({value})")


class LineTotalTest(Money):
    def setUp(self):
        self.line_total = importlib.import_module("billing.invoice").line_total

    def test_quantity_ties(self):
        cases = [((4.5, 0.25), "1.12"), ((0.125, 5), "0.62"), ((1.5, 0.25), "0.38"), ((2.125, 1), "2.12")]
        for args, expected in cases:
            self.assertMoney(call(self.line_total, *args), expected, f"line_total{args}")

    def test_discount_ties(self):
        cases = [((1.5, 1, 25), "1.12"), ((3.0, 1, 12.5), "2.62"), ((6.5, 1, 75), "1.62"), ((2.5, 1, 25), "1.88")]
        for args, expected in cases:
            self.assertMoney(call(self.line_total, *args), expected, f"line_total{args}")

    def test_ordinary_values(self):
        cases = [((19.99, 3), "59.97"), ((12.5, 3, 10), "33.75"), ((80.0, 1, 12.5), "70.00"), ((6.4, 12, 15), "65.28")]
        for args, expected in cases:
            self.assertMoney(call(self.line_total, *args), expected, f"line_total{args}")


class TaxAmountTest(Money):
    def setUp(self):
        self.tax_amount = importlib.import_module("billing.tax").tax_amount

    def test_ties(self):
        cases = [((5.0, 0.125), "0.62"), ((1.0, 0.125), "0.12"), ((4.5, 0.25), "1.12"), ((3.0, 0.125), "0.38")]
        for args, expected in cases:
            self.assertMoney(call(self.tax_amount, *args), expected, f"tax_amount{args}")

    def test_ordinary_values(self):
        cases = [((200.0, 0.07), "14.00"), ((59.97, 0.0825), "4.95"), ((120.0, 0), "0.00")]
        for args, expected in cases:
            self.assertMoney(call(self.tax_amount, *args), expected, f"tax_amount{args}")


class SplitInstallmentsTest(Money):
    def setUp(self):
        self.split = importlib.import_module("billing.payments").split_installments

    def test_ties(self):
        cases = [((0.25, 2), ["0.12", "0.13"]), ((10.25, 2), ["5.12", "5.13"]), ((2.75, 2), ["1.38", "1.37"])]
        for args, expected in cases:
            self.assertAmounts(call(self.split, *args), expected, f"split_installments{args}")

    def test_ordinary_values(self):
        cases = [
            ((100.0, 3), ["33.33", "33.33", "33.34"]),
            ((90.0, 4), ["22.50"] * 4),
            ((59.97, 1), ["59.97"]),
            ((157.94, 3), ["52.65", "52.65", "52.64"]),
        ]
        for args, expected in cases:
            self.assertAmounts(call(self.split, *args), expected, f"split_installments{args}")


TIE_ORDER = {
    "customer": "Quayside Deli",
    "tax_rate": 0.125,
    "items": [
        {"name": "Loose tea", "unit_price": 4.5, "quantity": 0.25},
        {"name": "Sugar sticks", "unit_price": 0.125, "quantity": 5},
        {"name": "Napkins", "unit_price": 1.5, "quantity": 1, "discount_percent": 25},
    ],
}
TAX_TIE_ORDER = {
    "customer": "Quayside Deli",
    "tax_rate": 0.125,
    "items": [{"name": "Delivery crate", "unit_price": 5.0, "quantity": 1}],
}
INSTALLMENT_ORDER = {
    "customer": "Quayside Deli",
    "installments": 2,
    "items": [{"name": "Service plan", "unit_price": 10.25, "quantity": 1}],
}
SAMPLE_ORDER = {
    "customer": "Harbor Street Cafe",
    "tax_rate": 0.0825,
    "installments": 3,
    "items": [
        {"name": "Espresso beans", "unit_price": 18.75, "quantity": 4},
        {"name": "Cane sugar", "unit_price": 2.25, "quantity": 2.5},
        {"name": "Paper cups", "unit_price": 6.4, "quantity": 12, "discount_percent": 15},
    ],
}


class BuildInvoiceTest(Money):
    def setUp(self):
        self.build_invoice = importlib.import_module("billing.invoice").build_invoice

    def check(self, order, subtotal, tax, total):
        invoice = call(self.build_invoice, order)
        self.assertMoney(invoice["subtotal"], subtotal, "subtotal")
        self.assertMoney(invoice["tax"], tax, "tax")
        self.assertMoney(invoice["total"], total, "total")

    def test_line_ties(self):
        self.check(TIE_ORDER, "2.86", "0.36", "3.22")

    def test_tax_tie(self):
        self.check(TAX_TIE_ORDER, "5.00", "0.62", "5.62")

    def test_sample_order(self):
        self.check(SAMPLE_ORDER, "145.90", "12.04", "157.94")


class CliTest(Money):
    def check(self, name, order, subtotal, tax, total, installments=None):
        output = run_cli(name, order)
        self.assertAmounts(row(output, "Subtotal")[-1:], [subtotal], "Subtotal")
        self.assertAmounts(row(output, "Tax")[-1:], [tax], "Tax")
        self.assertAmounts(row(output, "Total")[-1:], [total], "Total")
        if installments:
            self.assertAmounts(row(output, "Installments"), installments, "Installments")

    def test_line_ties(self):
        self.check("ties.json", TIE_ORDER, "2.86", "0.36", "3.22")

    def test_tax_tie(self):
        self.check("tax_tie.json", TAX_TIE_ORDER, "5.00", "0.62", "5.62")

    def test_installment_tie(self):
        self.check("installments.json", INSTALLMENT_ORDER, "10.25", "0.00", "10.25", ["5.12", "5.13"])

    def test_sample_order(self):
        self.check("sample.json", SAMPLE_ORDER, "145.90", "12.04", "157.94", ["52.65", "52.65", "52.64"])


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    with open(WORK / "behavior.log", "w") as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    problems = [test.id().split(".", 1)[1] for test, _ in result.failures + result.errors]
    print(json.dumps({"ran": result.testsRun, "ok": result.wasSuccessful(), "failed": problems}))


if __name__ == "__main__":
    main()
