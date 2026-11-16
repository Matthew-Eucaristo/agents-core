from decimal import Decimal

from pricing.money import to_cents
from pricing.orders import Order, Quote
from pricing.tax import sales_tax

BULK_TIERS = (
    (Decimal("5000.00"), Decimal("0.15")),
    (Decimal("2000.00"), Decimal("0.10")),
    (Decimal("500.00"), Decimal("0.05")),
)


def bulk_rate(subtotal: Decimal) -> Decimal:
    for threshold, rate in BULK_TIERS:
        if subtotal >= threshold:
            return rate
    return Decimal("0")


def apply_discount(order: Order) -> Quote:
    subtotal = order.subtotal
    discount = to_cents(subtotal * bulk_rate(subtotal))
    tax = sales_tax(subtotal - discount, order.region)
    return Quote(subtotal=subtotal, discount=discount, tax=tax, total=subtotal - discount + tax)
