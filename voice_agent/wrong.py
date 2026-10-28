def calculate_average(numbers):
    total = 0
    for num in numbers
        total += num
    return total / len(numbers)

def find_max(numbers):
    max_val = numbers[0]
    for i in range(1, len(numbers)):
        if numbers[i] > max_val:
            max_val = numbers[i]
    return max_val

data = [10, 25, 3, 47, 8, 19]
print("Average:", calculate_average(data))
print("Max:", find_max(data))
print("Total items:", len(data))