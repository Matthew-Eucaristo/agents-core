"""Loading of order rows from JSON files."""

import json


def load_rows(path):
    """Read the rows from a JSON file and check their shape."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    # The file must hold a list of objects, one per order line
    if not isinstance(data, list):
        raise ValueError("expected a list of rows")
    for index, row in enumerate(data):
        if not isinstance(row, dict):
            raise ValueError("row %d is not an object" % (index + 1))
    return data
