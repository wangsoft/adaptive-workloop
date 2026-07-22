import unittest

from auth import is_expired


class AuthTests(unittest.TestCase):
    def test_before_expiry_valid(self):
        self.assertFalse(is_expired({"exp": 100}, now=50))

    def test_after_expiry_expired(self):
        self.assertTrue(is_expired({"exp": 100}, now=150))

    def test_exact_expiry_is_expired(self):
        # Boundary: at the expiry instant the token must be expired.
        self.assertTrue(is_expired({"exp": 100}, now=100))


if __name__ == "__main__":
    unittest.main()
