import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from . import messages
from .errors import DropError

MANIFEST_NAME = "manifest.json"


@dataclass(frozen=True)
class Entry:
    name: str
    size: int
    sha256: str


def write_manifest(spool):
    spool = Path(spool)
    if not spool.is_dir():
        raise DropError(messages.SPOOL_MISSING.format(path=spool))
    files = []
    for path in sorted(spool.iterdir()):
        if path.is_file() and path.name != MANIFEST_NAME:
            data = path.read_bytes()
            files.append({"name": path.name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    (spool / MANIFEST_NAME).write_text(json.dumps({"files": files}, indent=2) + "\n")
    return len(files)


def load_manifest(spool):
    path = Path(spool) / MANIFEST_NAME
    try:
        raw = json.loads(path.read_text())
    except OSError as exc:
        raise DropError(messages.MANIFEST_UNREADABLE.format(path=path, reason=exc.strerror or exc)) from exc
    except ValueError as exc:
        raise DropError(messages.MANIFEST_INVALID.format(path=path, reason=exc)) from exc
    entries = {}
    for item in raw.get("files", []):
        entry = Entry(item["name"], int(item["size"]), item["sha256"])
        entries[entry.name] = entry
    return entries


def find_entry(spool, name):
    if "/" in name or "\\" in name:
        raise DropError(messages.UNSAFE_NAME.format(name=name))
    entries = load_manifest(spool)
    if name not in entries:
        raise DropError(messages.NOT_LISTED.format(name=name))
    return entries[name]
