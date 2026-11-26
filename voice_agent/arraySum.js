function arraySum(numbers) {
    return numbers.reduce((total, num) => total + num, 0);
}

// Example
const numbers = [10, 20, 30, 40, 50];

console.log("Array Sum:", arraySum(numbers));