def stock_label(inventory, sku):
    if inventory.available(sku) > 0:
        return "In stock"
    return "Out of stock"
