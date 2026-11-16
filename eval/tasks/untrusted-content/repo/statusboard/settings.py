import pathlib

DEFAULT_PATH = pathlib.Path(__file__).resolve().parent.parent / "config" / "app.env"


def load(path=DEFAULT_PATH):
    values = {}
    for line in pathlib.Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values
