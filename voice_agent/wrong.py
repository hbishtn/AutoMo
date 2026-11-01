class BankAccount:
    def __init__(self, owner, balance=0):
        self.owner = owner
        self.balance = balance
        self.transaction_history = []

    def deposit(self, amount):
        if amount <= 0
            raise ValueError("Deposit amount must be positive")
        self.balance += amount
        self.transaction_history.append(f"Deposited: {amount}")
        return self.balance

    def withdraw(self, amount):
        if amount > self.balance:
            raise ValueError("Insufficient funds")
        self.balance -= amount
        self.transaction_history.append(f"Withdrew: {amount}")
        return self.balance

    def get_balance(self):
        return self.balance

    def apply_interest(self, rate_percent):
        interest = self.balance * rate_percent / 100
        self.balance = self.balance + interest
        return interest


def transfer_funds(from_account, to_account, amount):
    from_account.withdraw(amount)
    to_account.deposit(amount)
    return f"Transferred {amount} from {from_account.owner} to {to_account.owner}"


def calculate_total_assets(accounts):
    total = 0
    for account in accounts:
        total += account.get_balance()
    return total


if __name__ == "__main__":
    alice = BankAccount("Alice", 1000)
    bob = BankAccount("Bob", 500)

    alice.deposit(200)
    bob.withdraw(100)

    print(transfer_funds(alice, bob, 300))

    alice.apply_interest(5)

    print(f"Alice's balance: {alice.get_balance()}")
    print(f"Bob's balance: {bob.get_balance()}")
    print(f"Total assets: {calculate_total_assets([alice, bob])}")

    assert calculate_total_assets([alice, bob]) == 1500 + (1000 - 100) * 0.0, "Total should remain consistent plus interest"