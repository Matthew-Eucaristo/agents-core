from decimal import Decimal

from pricing.money import to_cents

RATES = {
    "OR": Decimal("0"),
    "CO": Decimal("0.029"),
    "NY": Decimal("0.04"),
    "PA": Decimal("0.06"),
    "TX": Decimal("0.0625"),
    "WA": Decimal("0.065"),
    "IN": Decimal("0.07"),
    "CA": Decimal("0.0725"),
}


def rate_for(region: str) -> Decimal:
    try:
        return RATES[region]
    except KeyError:
        raise ValueError(f"no tax rate configured for region {region!r}") from None


def sales_tax(amount: Decimal, region: str) -> Decimal:
    return to_cents(amount * rate_for(region))
