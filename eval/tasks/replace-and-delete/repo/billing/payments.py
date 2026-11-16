from billing.rounding import round_price


def split_installments(total, count):
    if count < 1:
        raise ValueError("count must be at least 1")
    share = round_price(total / count)
    last = round_price(total - share * (count - 1))
    return [share] * (count - 1) + [last]
