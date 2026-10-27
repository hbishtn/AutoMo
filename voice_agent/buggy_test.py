body {
  margin: 0;
  font-family: Arial, sans-serif;
  background: #f4f6f9;
}

header {
  background: #172554;
  color: white;
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

nav a {
  color: white;
  text-decoration: none;
  margin-left: 20px;
}

.hero {
  text-align: center;
  padding: 60px 20px;
  background: #dbeafe;
}

button {
  background: #2563eb;
  color: white;
  padding: 10px 18px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.products {
  padding: 30px;
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.product-card {
  background: white;
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 2px 8px #00000015;
}

.contact {
  padding: 30px;
}

input {
  padding: 10px;
  margin-right: 10px;
}

footer {
  text-align: center;
  background: #172554;
  color: white;
  padding: 15px;
}