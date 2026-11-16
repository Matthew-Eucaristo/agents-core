import warnings
from decimal import ROUND_HALF_EVEN, Decimal

CENT = Decimal("0.01")


def round_money(value):
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_EVEN)


def round_price(value):
    warnings.warn("round_price is deprecated, use round_money", DeprecationWarning, stacklevel=2)
    return float(round_money(value))
