import unittest

from pagination import paginate


class PaginationTests(unittest.TestCase):
    items = list(range(1, 11))  # 1..10

    def test_first_page_is_first_slice(self):
        self.assertEqual(paginate(self.items, 1, 3), [1, 2, 3])

    def test_second_page(self):
        self.assertEqual(paginate(self.items, 2, 3), [4, 5, 6])

    def test_last_partial_page(self):
        self.assertEqual(paginate(self.items, 4, 3), [10])

    def test_page_out_of_range_is_empty(self):
        self.assertEqual(paginate(self.items, 5, 3), [])


if __name__ == "__main__":
    unittest.main()
