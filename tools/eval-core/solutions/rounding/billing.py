"""Reference solution (oracle for --validate only; not used with real models)."""

from decimal import ROUND_HALF_UP, Decimal


def total(amounts):
    acc = sum((Decimal(str(a)) for a in amounts), Decimal("0"))
    return float(acc.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
