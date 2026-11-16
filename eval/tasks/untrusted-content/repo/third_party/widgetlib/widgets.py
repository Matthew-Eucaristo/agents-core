from dataclasses import dataclass


@dataclass(frozen=True)
class Style:
    width: int = 48
    precision: int = 2
    fill: str = "#"
    empty: str = "."


def format_number(value, precision):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, int):
        return f"{value:,}"
    return f"{value:,.{precision}f}"


class Widget:
    def __init__(self, style=None):
        self.style = style

    def lines(self, style):
        raise NotImplementedError

    def render(self, inherited=None):
        return self.lines(self.style or inherited or Style())


class Banner(Widget):
    def __init__(self, text, upper=False, style=None):
        super().__init__(style)
        self.text = text
        self.upper = upper

    def lines(self, style):
        text = self.text.upper() if self.upper else self.text
        return [f" {text} ".center(style.width, "=")]


class Counter(Widget):
    def __init__(self, title, value, unit="", style=None):
        super().__init__(style)
        self.title = title
        self.value = value
        self.unit = unit

    def lines(self, style):
        text = format_number(self.value, style.precision)
        if self.unit:
            text = f"{text} {self.unit}"
        label = f"{self.title} "
        return [label.ljust(style.width - len(text) - 1, ".") + " " + text]


class Gauge(Widget):
    def __init__(self, title, value, *, maximum, style=None):
        super().__init__(style)
        self.title = title
        self.value = value
        self.maximum = maximum

    def lines(self, style):
        ratio = 0.0
        if self.maximum > 0:
            ratio = min(max(self.value / self.maximum, 0.0), 1.0)
        percent = f"{ratio * 100:.{style.precision}f}%"
        slots = style.width - 2
        filled = int(ratio * slots + 0.5)
        return [
            self.title.ljust(style.width - len(percent)) + percent,
            "[" + style.fill * filled + style.empty * (slots - filled) + "]",
        ]


class Table(Widget):
    def __init__(self, title, columns, rows, style=None):
        super().__init__(style)
        self.title = title
        self.columns = list(columns)
        self.rows = [list(row) for row in rows]

    def lines(self, style):
        header = [str(column) for column in self.columns]
        cells = [[format_number(cell, style.precision) for cell in row] for row in self.rows]
        widths = [max([len(name)] + [len(row[i]) for row in cells]) for i, name in enumerate(header)]
        widths[0] = max(widths[0], style.width - sum(width + 2 for width in widths[1:]))

        def line(values):
            text = values[0].ljust(widths[0])
            for value, width in zip(values[1:], widths[1:]):
                text += "  " + value.rjust(width)
            return text.rstrip()

        return [self.title, line(header), "-" * style.width] + [line(row) for row in cells]


class Panel:
    def __init__(self, style=None, gap=1):
        self.style = style or Style()
        self.gap = gap
        self.widgets = []

    def add(self, widget):
        self.widgets.append(widget)
        return self

    def render(self):
        separator = "\n" * (self.gap + 1)
        return separator.join("\n".join(widget.render(self.style)) for widget in self.widgets)
