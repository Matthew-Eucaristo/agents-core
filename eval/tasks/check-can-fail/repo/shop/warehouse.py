class Warehouse:
    def __init__(self, counts=None):
        self._counts = dict(counts or {})

    def count(self, sku):
        return self._counts.get(sku, 0)

    def add(self, sku, quantity):
        self._counts[sku] = self._counts.get(sku, 0) + quantity

    def remove(self, sku, quantity):
        self._counts[sku] = self._counts.get(sku, 0) - quantity
