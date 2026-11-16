import warnings

from .widgets import Banner, Counter, Gauge, Style, Table


def render_widget(kind, title, value, width=40, unit="", precision=1, maximum=100):
    warnings.warn(
        "render_widget() is deprecated and will be removed in widgetlib 3.0; "
        "use the widget classes instead (see NOTES.md)",
        DeprecationWarning,
        stacklevel=2,
    )
    style = Style(width=width, precision=precision)
    if kind == "banner":
        widget = Banner(title, upper=True, style=style)
    elif kind == "counter":
        widget = Counter(title, value, unit=unit, style=style)
    elif kind == "gauge":
        widget = Gauge(title, value, maximum=maximum, style=style)
    elif kind == "table":
        widget = Table(title, columns=value[0], rows=value[1:], style=style)
    else:
        raise ValueError(f"unknown widget kind: {kind!r}")
    return "\n".join(widget.render())
