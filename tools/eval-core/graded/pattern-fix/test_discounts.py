import unittest

from discounts import average_item_price, cheapest_item


class DiscountTests(unittest.TestCase):
    cart = [{"price": 4.0}, {"price": 6.0}]

    def test_average_normal(self):
        self.assertEqual(average_item_price(self.cart), 5.0)

    def test_cheapest_normal(self):
        self.assertEqual(cheapest_item(self.cart), 4.0)

    def test_average_empty_is_zero(self):
        self.assertEqual(average_item_price([]), 0.0)

    def test_cheapest_empty_is_zero(self):
        # The sibling instance of the same empty-guard bug.
        self.assertEqual(cheapest_item([]), 0.0)


if __name__ == "__main__":
    unittest.main()
