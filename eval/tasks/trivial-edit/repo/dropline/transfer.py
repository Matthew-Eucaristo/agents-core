import hashlib
import os
from pathlib import Path

from . import messages
from .errors import DropError
from .manifest import find_entry

CHUNK_SIZE = 64 * 1024


def receive(spool, name, dest_dir, overwrite=False):
    entry = find_entry(spool, name)
    source = Path(spool) / entry.name
    dest_dir = Path(dest_dir)
    target = dest_dir / entry.name
    if target.exists() and not overwrite:
        raise DropError(messages.DEST_EXISTS.format(path=target))
    dest_dir.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    digest = hashlib.sha256()
    received = 0
    try:
        with open(source, "rb") as reader, open(partial, "wb") as writer:
            while chunk := reader.read(CHUNK_SIZE):
                writer.write(chunk)
                digest.update(chunk)
                received += len(chunk)
    except OSError as exc:
        _discard(partial)
        raise DropError(messages.RECEIVE_FAILED.format(name=name, reason=exc.strerror or exc)) from exc
    if received != entry.size:
        _discard(partial)
        reason = f"got {received} of {entry.size} bytes"
        raise DropError(messages.RECEIVE_FAILED.format(name=name, reason=reason))
    if digest.hexdigest() != entry.sha256:
        _discard(partial)
        raise DropError(messages.CHECKSUM_MISMATCH.format(name=name))
    os.replace(partial, target)
    return target


def _discard(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
