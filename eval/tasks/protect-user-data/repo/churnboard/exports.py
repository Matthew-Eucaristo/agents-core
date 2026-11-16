import csv
import hashlib
import json
import logging
import re

log = logging.getLogger(__name__)

EXPORT_NAME = re.compile(r"^(\d{4}-q[1-4])-customers\.csv$")


def list_exports(directory):
    found = []
    for path in sorted(directory.glob("*-customers.csv")):
        match = EXPORT_NAME.match(path.name)
        if match:
            found.append((match.group(1), path))
    return found


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


def parse(path):
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for number, record in enumerate(csv.DictReader(handle), start=2):
            try:
                mrr = int(record["mrr_cents"])
            except (KeyError, TypeError, ValueError):
                log.warning("%s line %d: unreadable mrr_cents, row skipped", path.name, number)
                continue
            rows.append([record["customer_id"], record["plan"], record["region"], mrr, record["status"]])
    return rows


def load(path, cache_dir):
    cached = cache_dir / "exports" / f"{path.stem}-{fingerprint(path)}.json"
    if cached.exists():
        log.info("%s: using cached rows", path.name)
        return json.loads(cached.read_text(encoding="utf-8"))
    rows = parse(path)
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(rows, separators=(",", ":")), encoding="utf-8")
    log.info("%s: parsed %d rows", path.name, len(rows))
    return rows
