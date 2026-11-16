"""Export helpers for report rows.

A row is a plain dict that maps a column name to a value. Every output
format is one function in this module named to_<format>(rows), and it
returns the finished text. The command line looks the function up by
that name from the --format option.
"""

import json


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


def to_json(rows):
    """Export the rows as a JSON array with one object per row."""
    # Indent by two spaces so the output is easy to read in a diff
    text = json.dumps(list(rows), indent=2, ensure_ascii=False)
    # Finish with a newline so the output can be redirected to a file
    return text + "\n"


def to_text(rows):
    """Export the rows as a plain text table with aligned columns."""
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
