from shop.storefront import stock_label
from tests.base import ShopTestCase


class StorefrontTest(ShopTestCase):
    def test_label_for_stocked_item(self):
        self.assertEqual(stock_label(self.inventory, "mug"), "In stock")

    def test_label_for_empty_item(self):
        self.assertEqual(stock_label(self.inventory, "poster"), "Out of stock")
