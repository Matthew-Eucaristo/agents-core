import unittest

from shop import settings
from shop.inventory import Inventory
from shop.warehouse import Warehouse


class ShopTestCase(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, settings, "CACHE_STOCK", settings.CACHE_STOCK)
        settings.CACHE_STOCK = False
        self.warehouse = Warehouse({"mug": 3, "poster": 0})
        self.inventory = Inventory(self.warehouse)
