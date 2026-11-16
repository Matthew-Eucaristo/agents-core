import csv
import io

from utils.dates import month_bounds
from utils.text import slugify


def export_csv(rows, columns):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row.get(column, "") for column in columns])
    return buffer.getvalue()


def export_filename(title, day):
    first, last = month_bounds(day)
    return f"{slugify(title)}_{first:%Y%m%d}-{last:%Y%m%d}.csv"
