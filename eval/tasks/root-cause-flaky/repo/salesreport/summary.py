from collections import defaultdict


def summarize(orders):
    by_region = defaultdict(float)
    by_product = defaultdict(float)
    units = 0
    for order in orders:
        by_region[order.region] += order.total
        by_product[order.product] += order.total
        units += order.quantity
    top_product = max(sorted(by_product), key=by_product.get) if by_product else None
    return {
        "orders": len(orders),
        "units": units,
        "revenue": round(sum(by_region.values()), 2),
        "by_region": {region: round(by_region[region], 2) for region in sorted(by_region)},
        "top_product": top_product,
    }


def render(summary):
    lines = [
        f"Orders:      {summary['orders']}",
        f"Units:       {summary['units']}",
        f"Revenue:     {summary['revenue']:.2f}",
        f"Top product: {summary['top_product'] or '-'}",
    ]
    for region, revenue in summary["by_region"].items():
        lines.append(f"  {region:<10} {revenue:>10.2f}")
    return "\n".join(lines)
