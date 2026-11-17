from shop import settings
from shop.inventory import OutOfStock
from tests.base import ShopTestCase


class InventoryTest(ShopTestCase):
    def test_available_reads_the_warehouse(self):
        self.assertEqual(self.inventory.available("mug"), 3)

    def test_reserve_takes_stock(self):
        self.inventory.reserve("mug", 2)
        self.assertEqual(self.inventory.available("mug"), 1)

    def test_reserve_more_than_available_is_refused(self):
        with self.assertRaises(OutOfStock):
            self.inventory.reserve("mug", 4)

    def test_reserve_rejects_zero(self):
        with self.assertRaises(ValueError):
            self.inventory.reserve("mug", 0)

    def test_restock_rejects_zero(self):
        with self.assertRaises(ValueError):
            self.inventory.restock("mug", 0)

    def test_restock_shows_at_once_while_stock_is_cached(self):
        settings.CACHE_STOCK = True
        self.assertEqual(self.inventory.available("poster"), 0)
        self.inventory.restock("poster", 5)
        self.assertEqual(self.inventory.available("poster"), 5)
