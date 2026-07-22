import unittest

from billing import total


class BillingTests(unittest.TestCase):
    def test_simple_sum_no_drift(self):
        self.assertEqual(total([0.1, 0.2]), 0.3)

    def test_half_up_at_cent(self):
        # 2.675 must round up to 2.68 (float round() gives 2.67).
        self.assertEqual(total([2.675]), 2.68)

    def test_many_small_amounts(self):
        self.assertEqual(total([0.005, 0.005]), 0.01)

    def test_empty_is_zero(self):
        self.assertEqual(total([]), 0.0)


if __name__ == "__main__":
    unittest.main()
