"""Invoice total. BUG: binary-float drift + inconsistent rounding."""


def total(amounts):
    # Must be correct to the cent with half-up rounding.
    # BUG: float sum drifts and round() is banker's rounding, not half-up.
    return round(sum(amounts), 2)
