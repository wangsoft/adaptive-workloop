"""Exponential backoff. BUG: ignores the cap and returns the wrong count."""


def backoff_delays(attempts, base, cap):
    # Return exactly `attempts` delays: base * 2**i, each clamped to `cap`.
    # BUG: off-by-one count and no cap applied.
    return [base * (2 ** i) for i in range(attempts - 1)]
