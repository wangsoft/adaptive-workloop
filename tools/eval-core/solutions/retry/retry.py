"""Reference solution (oracle for --validate only; not used with real models)."""


def backoff_delays(attempts, base, cap):
    return [min(cap, base * (2 ** i)) for i in range(attempts)]
