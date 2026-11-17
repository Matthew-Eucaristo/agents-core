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
