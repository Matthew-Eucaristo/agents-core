from billing import rounding


def tax_amount(amount, rate):
    return rounding.round_price(amount * rate)
