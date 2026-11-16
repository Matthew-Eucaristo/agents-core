from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Line:
    sku: str
    unit_price: Decimal
    quantity: int


@dataclass(frozen=True)
class Order:
    region: str
    lines: tuple[Line, ...]

    @property
    def subtotal(self) -> Decimal:
        return sum((line.unit_price * line.quantity for line in self.lines), Decimal("0.00"))


@dataclass(frozen=True)
class Quote:
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal
