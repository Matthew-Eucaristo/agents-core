from pathlib import Path


class Paths:
    def __init__(self, root):
        self.root = Path(root)
        self.exports = self.root / "data" / "exports"
        self.database = self.root / "data" / "customers.db"
        self.cache = self.root / ".cache"
        self.output = self.root / "build"
        self.logs = self.root / "logs"
