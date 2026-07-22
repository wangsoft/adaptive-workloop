import unittest

from retry import backoff_delays


class RetryTests(unittest.TestCase):
    def test_count_matches_attempts(self):
        self.assertEqual(len(backoff_delays(5, base=1, cap=100)), 5)

    def test_first_delay_is_base(self):
        self.assertEqual(backoff_delays(3, base=2, cap=100)[0], 2)

    def test_grows_exponentially_until_cap(self):
        self.assertEqual(backoff_delays(4, base=1, cap=100), [1, 2, 4, 8])

    def test_delays_are_capped(self):
        self.assertTrue(all(d <= 10 for d in backoff_delays(8, base=1, cap=10)))


if __name__ == "__main__":
    unittest.main()
