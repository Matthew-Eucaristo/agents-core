from billing.rounding import round_price
from billing.tax import tax_amount


def line_total(unit_price, quantity, discount_percent=0):
    gross = unit_price * quantity
    return round_price(gross * (100 - discount_percent) / 100)


def build_invoice(order):
    lines = [
        (
            item["name"],
            line_total(item["unit_price"], item["quantity"], item.get("discount_percent", 0)),
        )
        for item in order["items"]
    ]
    subtotal = round_price(sum(amount for _, amount in lines))
    tax = tax_amount(subtotal, order.get("tax_rate", 0))
    return {
        "customer": order["customer"],
        "lines": lines,
        "subtotal": subtotal,
        "tax": tax,
        "total": subtotal + tax,
    }
