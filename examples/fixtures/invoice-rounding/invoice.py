"""Minimal invoice rounding fixture used by the verified-episode example."""

from decimal import Decimal, ROUND_HALF_UP


def invoice_total(line_items: list[str], tax_rate: str = "0") -> Decimal:
    subtotal = sum((Decimal(value) for value in line_items), start=Decimal("0"))
    total = subtotal * (Decimal("1") + Decimal(tax_rate))
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
