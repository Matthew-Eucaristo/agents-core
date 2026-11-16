from billing.rounding import round_money, to_decimal


def split_installments(total, count):
    if count < 1:
        raise ValueError("count must be at least 1")
    total = to_decimal(total)
    share = round_money(total / count)
    last = round_money(total - share * (count - 1))
    return [share] * (count - 1) + [last]
