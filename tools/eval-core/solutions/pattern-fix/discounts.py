"""Reference solution (oracle for --validate only; not used with real models)."""


def average_item_price(cart):
    if not cart:
        return 0.0
    total = sum(item["price"] for item in cart)
    return total / len(cart)


def cheapest_item(cart):
    if not cart:
        return 0.0
    return min(cart, key=lambda item: item["price"])["price"]
