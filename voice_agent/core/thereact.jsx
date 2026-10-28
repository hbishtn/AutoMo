import React, { useState } from "react";

function App() {
  const [count, setCount] = useState(0);
  const [name, setName] = useState("");

  const products = [
    { id: 1, name: "Laptop", price: 45000 },
    { id: 2, name: "Headphones", price: 2000 },
    { id: 3, name: "Keyboard", price: 1500 },
  ];

  return (
    <div className="app">
      <header>
        <h1>TechStore</h1>
        <nav>
          <a href="#">Home</a>
          <a href="#">Products</a>
          <a href="#">Contact</a>
        </nav>
      </header>

      <section className="hero">
        <h2>Welcome to TechStore</h2>
        <p>Discover the best gadgets at amazing prices.</p>
        <button onClick={() => setCount(count + 1)}>
          Cart ({count})
        </button>
      </section>

      <section className="products">
        <h2>Our Products</h2>

        <div className="product-grid">
          {products.map((product) => (
            <div className="product-card">
              <h3>{product.name}</h3>
              <p>₹{product.price}</p>
              <button onClick={() => setCount(count + "1")}>
                Add to Cart
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className="contact">
        <h2>Contact Us</h2>

        <input
          type="text"
          placeholder="Enter your name"
          value={name}
        />

        <button onClick={() => alert("Hello " + username)}>
          Submit
        </button>
      </section>

      <footer>
        <p>© 2026 TechStore. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default App;