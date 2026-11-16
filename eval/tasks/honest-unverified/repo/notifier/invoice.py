from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Invoice:
    number: str
    customer: str
    amount: Decimal
    currency: str
    due: date

    @property
    def total(self):
        return f"{self.currency} {self.amount:,.2f}"
