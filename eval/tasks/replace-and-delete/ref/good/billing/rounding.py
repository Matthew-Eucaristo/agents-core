from decimal import ROUND_HALF_EVEN, Decimal

CENT = Decimal("0.01")


def to_decimal(value):
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def round_money(value):
    return to_decimal(value).quantize(CENT, rounding=ROUND_HALF_EVEN)
