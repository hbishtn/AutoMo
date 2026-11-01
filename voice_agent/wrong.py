class BankAccount:
    def __init__(self, owner, balance=0):
        self.owner = owner
        self.balance = balance
        self.transaction_history = []


    def deposit(self, amount):
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self.balance += amount
        self.transaction_history.append(f"Deposited: {amount}")
        return self.balance


    def get_balance(self):
        return self.balance




if __name__ == "__main__":
    alice = BankAccount("Alice", 1000)
    alice.deposit(200)
    print(f"Alice's balance: {alice.get_balance()}")