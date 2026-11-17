import time

from shop import settings


class OutOfStock(Exception):
    pass


class Inventory:
    def __init__(self, warehouse, clock=time.monotonic):
        self._warehouse = warehouse
        self._clock = clock
        self._cached = {}

    def available(self, sku):
        if not settings.CACHE_STOCK:
            return self._warehouse.count(sku)
        cached = self._cached.get(sku)
        now = self._clock()
        if cached is not None and now - cached[1] < settings.STOCK_CACHE_SECONDS:
            return cached[0]
        count = self._warehouse.count(sku)
        self._cached[sku] = (count, now)
        return count

    def reserve(self, sku, quantity):
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if quantity > self.available(sku):
            raise OutOfStock(sku)
        self._warehouse.remove(sku, quantity)
        self._cached.pop(sku, None)

    def restock(self, sku, quantity):
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        self._warehouse.add(sku, quantity)
        self._cached.pop(sku, None)
