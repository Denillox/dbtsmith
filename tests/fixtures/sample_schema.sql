CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    email TEXT,
    region TEXT
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    email TEXT,
    order_total NUMERIC,
    order_date DATE
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT,
    category TEXT
);

ALTER TABLE orders ADD COLUMN product_id INTEGER;
UPDATE orders SET product_id = 1 WHERE id IN (1, 3);

INSERT INTO products (id, name, category) VALUES
    (1, 'Widget', 'Hardware'),
    (2, 'Gadget', 'Electronics');

INSERT INTO customers (id, email, region) VALUES
    (1, 'a@example.com', 'EU'),
    (2, 'b@example.com', 'US');

INSERT INTO orders (id, customer_id, email, order_total, order_date) VALUES
    (1, 1, 'a@example.com', 100.00, '2025-01-15'),
    (2, 1, 'a@example.com', 100.00, '2025-01-15'),
    (3, 2, 'b@example.com', 250.00, '2025-02-03');