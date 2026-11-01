def calculate_total(price, quantity, discount_percent):
    subtotal = price * quantity
    discount_amount = subtotal * (discount_percent / 100)
    total = subtotal + discount_amount  # BUG: should be subtotal - discount_amount
    return total

def apply_ tax(amount, tax_rate):
    return amount * (1 + tax_rate / 100)

price = 50
quantity = 3
discount = 10
tax = 8

total_before_tax = calculate_total(price, quantity, discount)
final_total = apply_tax(total_before_tax, tax)

print(f"Subtotal: {price * quantity}")
print(f"After discount: {total_before_tax}")
 print(f"Final total with tax: {final_total}")

assert total_before_tax < (price * quantity), "Discount should reduce the price!"