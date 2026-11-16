import csv
from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    order_id: str
    region: str
    product: str
    quantity: int
    unit_price: float

    @property
    def total(self):
        return self.quantity * self.unit_price


class CsvOrderSource:
    def __init__(self, path):
        self.path = path

    def fetch(self):
        with open(self.path, newline="") as handle:
            return [
                Order(
                    order_id=row["order_id"],
                    region=row["region"],
                    product=row["product"],
                    quantity=int(row["quantity"]),
                    unit_price=float(row["unit_price"]),
                )
                for row in csv.DictReader(handle)
            ]
