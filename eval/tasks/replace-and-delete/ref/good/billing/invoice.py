from billing.rounding import round_money, to_decimal
from billing.tax import tax_amount


def line_total(unit_price, quantity, discount_percent=0):
    gross = to_decimal(unit_price) * to_decimal(quantity)
    return round_money(gross * (100 - to_decimal(discount_percent)) / 100)


def build_invoice(order):
    lines = [
        (
            item["name"],
            line_total(item["unit_price"], item["quantity"], item.get("discount_percent", 0)),
        )
        for item in order["items"]
    ]
    subtotal = round_money(sum(amount for _, amount in lines))
    tax = tax_amount(subtotal, order.get("tax_rate", 0))
    return {
        "customer": order["customer"],
        "lines": lines,
        "subtotal": subtotal,
        "tax": tax,
        "total": subtotal + tax,
    }
