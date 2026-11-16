from third_party.widgetlib import render_widget

WIDTH = 44
LATE_COLUMNS = ("carrier", "orders", "delay h")


def render_report(snapshot, config):
    parts = [
        render_widget("banner", config["BOARD_TITLE"], None, width=WIDTH),
        render_widget("counter", "Open orders", snapshot["open_orders"], width=WIDTH),
        render_widget(
            "counter", "Stock value", snapshot["stock_value"], width=WIDTH, unit=config["CURRENCY"], precision=2
        ),
        render_widget("counter", "Avg pick time", snapshot["avg_pick_minutes"], width=WIDTH, unit="min"),
        render_widget(
            "gauge", "Dock utilisation", snapshot["docks_busy"], width=WIDTH, maximum=snapshot["docks_total"]
        ),
        render_widget("gauge", "Shelf fill", snapshot["shelf_fill_percent"], width=WIDTH),
    ]
    late = snapshot.get("late_shipments") or []
    if late:
        rows = [LATE_COLUMNS]
        for shipment in late:
            rows.append((shipment["carrier"], shipment["orders"], shipment["delay_hours"]))
        parts.append(render_widget("table", "Late shipments", rows, width=WIDTH))
    return "\n\n".join(parts) + "\n"


def render_brief(snapshot):
    lines = [
        render_widget("counter", "Open orders", snapshot["open_orders"]),
        render_widget("counter", "Avg pick time", snapshot["avg_pick_minutes"], unit="min"),
        render_widget("gauge", "Shelf fill", snapshot["shelf_fill_percent"]),
    ]
    return "\n".join(lines) + "\n"
