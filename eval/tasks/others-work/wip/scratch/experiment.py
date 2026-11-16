import json

ROWS = [
    {"region": "North", "orders": 12, "revenue": "1840.50"},
    {"region": "South, coastal", "orders": 7},
]
COLUMNS = ["region", "orders", "revenue"]


def with_blanks(rows, columns):
    return [{column: row.get(column, "") for column in columns} for row in rows]


def with_nulls(rows, columns):
    return [{column: row.get(column) for column in columns} for row in rows]


if __name__ == "__main__":
    for shape in (with_blanks, with_nulls):
        print(shape.__name__)
        print(json.dumps(shape(ROWS, COLUMNS), indent=2))
