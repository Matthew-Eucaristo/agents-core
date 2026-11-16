from third_party.widgetlib import Banner, Counter, Gauge, Panel, Style, Table

BOARD_STYLE = Style(width=44, precision=1)
BRIEF_STYLE = Style(width=40, precision=1)
MONEY_STYLE = Style(width=44, precision=2)
LATE_COLUMNS = ("carrier", "orders", "delay h")


def render_report(snapshot, config):
    panel = Panel(BOARD_STYLE)
    panel.add(Banner(config["BOARD_TITLE"], upper=True))
    panel.add(Counter("Open orders", snapshot["open_orders"]))
    panel.add(Counter("Stock value", snapshot["stock_value"], unit=config["CURRENCY"], style=MONEY_STYLE))
    panel.add(Counter("Avg pick time", snapshot["avg_pick_minutes"], unit="min"))
    panel.add(Gauge("Dock utilisation", snapshot["docks_busy"], maximum=snapshot["docks_total"]))
    panel.add(Gauge("Shelf fill", snapshot["shelf_fill_percent"], maximum=100))
    late = snapshot.get("late_shipments") or []
    if late:
        rows = [(shipment["carrier"], shipment["orders"], shipment["delay_hours"]) for shipment in late]
        panel.add(Table("Late shipments", columns=LATE_COLUMNS, rows=rows))
    return panel.render() + "\n"


def render_brief(snapshot):
    panel = Panel(BRIEF_STYLE, gap=0)
    panel.add(Counter("Open orders", snapshot["open_orders"]))
    panel.add(Counter("Avg pick time", snapshot["avg_pick_minutes"], unit="min"))
    panel.add(Gauge("Shelf fill", snapshot["shelf_fill_percent"], maximum=100))
    return panel.render() + "\n"
