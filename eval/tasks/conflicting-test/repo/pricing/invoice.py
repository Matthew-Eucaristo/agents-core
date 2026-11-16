from pricing.discounts import apply_discount
from pricing.money import format_money
from pricing.orders import Order, Quote


def render(order: Order, quote: Quote) -> list[str]:
    rows = [
        f"{line.quantity} x {line.sku} @ {format_money(line.unit_price)}"
        for line in order.lines
    ]
    rows.append(f"Subtotal {format_money(quote.subtotal)}")
    if quote.discount:
        rows.append(f"Bulk discount -{format_money(quote.discount)}")
    rows.append(f"Tax ({order.region}) {format_money(quote.tax)}")
    rows.append(f"Total {format_money(quote.total)}")
    return rows


def invoice_for(order: Order) -> list[str]:
    return render(order, apply_discount(order))
