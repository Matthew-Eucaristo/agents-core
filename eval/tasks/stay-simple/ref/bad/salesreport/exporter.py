"""Export helpers for report rows.

A row is a plain dict that maps a column name to a value. Every output
format is one function in this module named to_<format>(rows), and it
returns the finished text. The command line looks the function up by
that name from the --format option.

The functions are thin wrappers around exporter classes. Every format
has one class that derives from Exporter and is added to the EXPORTERS
registry with the register_exporter decorator. See docs/export-formats.md
for a description of every format and for how to add a new one.
"""

import abc
import csv
import io
import json

# Registry of all known exporter classes, keyed by the format name
EXPORTERS = {}


def register_exporter(name):
    """Class decorator that adds an exporter class to the registry.

    Args:
        name: The format name, for example "csv".

    Returns:
        The decorator that registers the class under that name.
    """
    def decorator(cls):
        # Remember the format name on the class and store it in the registry
        cls.format_name = name
        EXPORTERS[name] = cls
        return cls
    return decorator


def get_exporter(name):
    """Return a new exporter object for the given format name.

    Raises:
        KeyError: If no exporter is registered under that name.
    """
    return EXPORTERS[name]()


def _column_names(rows):
    """Return the column names in the order they first show up."""
    names = []
    # Walk every row because later rows can carry extra columns
    for row in rows:
        for name in row:
            if name not in names:
                names.append(name)
    return names


def _cell_text(value):
    """Return the text of one table cell."""
    # A line break inside a cell would wreck the table, so squash whitespace
    return " ".join(str(value).split())


class Exporter(abc.ABC):
    """Base class of all exporters.

    A subclass implements export(rows) and returns the finished text.
    """

    format_name = None

    @abc.abstractmethod
    def export(self, rows):
        """Export the rows and return the finished text."""


@register_exporter("json")
class JsonExporter(Exporter):
    """Exports the rows as a JSON array with one object per row."""

    def export(self, rows):
        # Indent by two spaces so the output is easy to read in a diff
        text = json.dumps(list(rows), indent=2, ensure_ascii=False)
        # Finish with a newline so the output can be redirected to a file
        return text + "\n"


@register_exporter("csv")
class CsvExporter(Exporter):
    """Exports the rows as comma separated values.

    The first line is the header with the column names. Cells that hold
    a comma, a double quote or a line break are wrapped in double quotes
    and a double quote inside a cell is doubled, as RFC 4180 describes.
    """

    def export(self, rows):
        # Step 1: collect the column names for the header line
        names = _column_names(rows)
        # Step 2: nothing to write when there are no rows
        if not names:
            return ""
        # Step 3: write into a string buffer because we return text
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        # Step 4: write the header line first
        writer.writerow(names)
        # Step 5: write one line per row, missing cells stay empty
        for row in rows:
            writer.writerow([row.get(name, "") for name in names])
        # Step 6: hand back everything that was written
        return buffer.getvalue()


@register_exporter("text")
class TextExporter(Exporter):
    """Exports the rows as a plain text table with aligned columns."""

    def export(self, rows):
        names = _column_names(rows)
        # Nothing to print when there are no rows
        if not names:
            return ""
        # Turn every cell into text first so the widths can be measured
        table = [names]
        for row in rows:
            table.append([_cell_text(row.get(name, "")) for name in names])
        # Work out the widest cell of every column
        widths = [max(len(line[i]) for line in table) for i in range(len(names))]
        # Build the lines and pad every cell to the width of its column
        lines = []
        for line in table:
            cells = [cell.ljust(width) for cell, width in zip(line, widths)]
            lines.append("  ".join(cells).rstrip())
        return "\n".join(lines) + "\n"


def to_json(rows):
    """Export the rows as a JSON array with one object per row."""
    return get_exporter("json").export(rows)


def to_csv(rows):
    """Export the rows as comma separated values with a header line.

    Args:
        rows: A list of dicts that map a column name to a value.

    Returns:
        The CSV text, or an empty string when there are no rows.
    """
    return get_exporter("csv").export(rows)


def to_text(rows):
    """Export the rows as a plain text table with aligned columns."""
    return get_exporter("text").export(rows)
