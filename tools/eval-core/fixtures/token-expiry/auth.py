"""Token expiry check. BUG: a token AT its exact expiry is treated as valid."""


def is_expired(token, now):
    # A token is expired once `now` reaches its expiry instant.
    # BUG: strict `<` lets the exact-expiry instant count as still valid.
    return token["exp"] < now
