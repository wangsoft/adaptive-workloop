import unittest

from invoice import invoice_total


class InvoiceRoundingTests(unittest.TestCase):
    def test_rounds_half_up_at_the_currency_boundary(self) -> None:
        self.assertEqual(str(invoice_total(["19.995"])), "20.00")

    def test_applies_tax_before_rounding(self) -> None:
        self.assertEqual(str(invoice_total(["10.00", "5.55"], "0.0825")), "16.83")

    def test_decimal_input_avoids_binary_float_drift(self) -> None:
        self.assertEqual(str(invoice_total(["0.10", "0.20"])), "0.30")


if __name__ == "__main__":
    unittest.main()
