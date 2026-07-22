"""Pagination helper. BUG: page 1 skips the first page of items."""


def paginate(items, page, per_page):
    # Pages are 1-indexed: page 1 must return the first `per_page` items.
    # BUG: uses page directly as a 0-indexed multiplier.
    start = page * per_page
    end = start + per_page
    return items[start:end]
