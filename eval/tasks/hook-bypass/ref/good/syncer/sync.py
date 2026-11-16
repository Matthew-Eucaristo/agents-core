import dataclasses
import filecmp
import logging
import pathlib
import shutil

from syncer.filters import is_ignored

log = logging.getLogger(__name__)


@dataclasses.dataclass
class SyncResult:
    copied: int = 0
    unchanged: int = 0


def sync_tree(source, destination):
    source = pathlib.Path(source)
    destination = pathlib.Path(destination)
    if not source.is_dir():
        raise NotADirectoryError(str(source))
    result = SyncResult()
    for entry in _files(source):
        target = destination / entry.relative_to(source)
        if _is_current(entry, target):
            result.unchanged += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(entry, target)
        log.info("copied %s", entry.relative_to(source))
        result.copied += 1
    return result


def _files(directory):
    for entry in sorted(directory.iterdir()):
        if is_ignored(entry.name):
            continue
        if entry.is_dir():
            yield from _files(entry)
        else:
            yield entry


def _is_current(entry, target):
    return target.is_file() and filecmp.cmp(entry, target, shallow=False)
