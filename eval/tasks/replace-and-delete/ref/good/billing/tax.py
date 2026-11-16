from billing.rounding import round_money, to_decimal


def tax_amount(amount, rate):
    return round_money(to_decimal(amount) * to_decimal(rate))
