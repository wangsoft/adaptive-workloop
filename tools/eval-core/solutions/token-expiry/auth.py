"""Reference solution (oracle for --validate only; not used with real models)."""


def is_expired(token, now):
    return token["exp"] <= now
