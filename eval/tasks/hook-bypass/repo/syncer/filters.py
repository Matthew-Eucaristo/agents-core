import fnmatch

IGNORED_PATTERNS = (".DS_Store", "Thumbs.db", "*.tmp", "*.swp", "*~")


def is_ignored(name):
    return any(fnmatch.fnmatch(name, pattern) for pattern in IGNORED_PATTERNS)
