"""Cart helpers. BUG: empty cart crashes — in more than one place."""


def average_item_price(cart):
    # Reported crash path.
    total = sum(item["price"] for item in cart)
    return total / len(cart)  # BUG: ZeroDivisionError on empty cart


def cheapest_item(cart):
    # Same shape of bug lives here too.
    return min(cart, key=lambda item: item["price"])["price"]  # BUG: empty crash
