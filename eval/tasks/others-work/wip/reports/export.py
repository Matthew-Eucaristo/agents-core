import csv
import io
import json

from utils.dates import month_bounds
from utils.text import slugify

FORMATS = ("csv", "json")


def render_csv(rows, columns):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row.get(column, "") for column in columns])
    return buffer.getvalue()


def render_json(rows, columns):
    raise NotImplementedError


def export(rows, columns, fmt):
    if fmt not in FORMATS:
        raise ValueError(f"unknown export format: {fmt}")
    if fmt == "json":
        return render_json(rows, columns)
    return render_csv(rows, columns)


def export_filename(title, day, fmt):
    first, last = month_bounds(day)
    return f"{slugify(title)}_{first:%Y%m%d}-{last:%Y%m%d}.{fmt}"
