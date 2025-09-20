-- Sample data for GenBI testing
-- This creates a typical e-commerce database structure

-- Create customers table
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    city VARCHAR(50),
    state VARCHAR(50),
    country VARCHAR(50),
    postal_code VARCHAR(20),
    registration_date DATE DEFAULT CURRENT_DATE,
    customer_segment VARCHAR(20) DEFAULT 'Regular'
);

-- Create products table
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(200) NOT NULL,
    category VARCHAR(50),
    subcategory VARCHAR(50),
    brand VARCHAR(50),
    unit_price DECIMAL(10,2) NOT NULL,
    cost_price DECIMAL(10,2),
    stock_quantity INTEGER DEFAULT 0,
    reorder_level INTEGER DEFAULT 10,
    supplier_id INTEGER,
    created_date DATE DEFAULT CURRENT_DATE,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create orders table
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    order_date DATE DEFAULT CURRENT_DATE,
    ship_date DATE,
    delivery_date DATE,
    order_status VARCHAR(20) DEFAULT 'Pending',
    shipping_cost DECIMAL(8,2) DEFAULT 0,
    tax_amount DECIMAL(8,2) DEFAULT 0,
    discount_amount DECIMAL(8,2) DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(20),
    shipping_address TEXT,
    region VARCHAR(50)
);

-- Create order_items table
CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(order_id),
    product_id INTEGER REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    discount_percent DECIMAL(5,2) DEFAULT 0,
    line_total DECIMAL(10,2) NOT NULL
);

-- Create suppliers table
CREATE TABLE suppliers (
    supplier_id SERIAL PRIMARY KEY,
    supplier_name VARCHAR(100) NOT NULL,
    contact_person VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    address TEXT,
    city VARCHAR(50),
    country VARCHAR(50),
    rating DECIMAL(3,2)
);

-- Insert sample customers
INSERT INTO customers (customer_name, email, phone, city, state, country, customer_segment) VALUES
('John Smith', 'john.smith@email.com', '555-0101', 'New York', 'NY', 'USA', 'Premium'),
('Sarah Johnson', 'sarah.j@email.com', '555-0102', 'Los Angeles', 'CA', 'USA', 'Regular'),
('Mike Brown', 'mike.brown@email.com', '555-0103', 'Chicago', 'IL', 'USA', 'Premium'),
('Emily Davis', 'emily.d@email.com', '555-0104', 'Houston', 'TX', 'USA', 'Regular'),
('David Wilson', 'david.w@email.com', '555-0105', 'Phoenix', 'AZ', 'USA', 'VIP'),
('Lisa Anderson', 'lisa.a@email.com', '555-0106', 'Philadelphia', 'PA', 'USA', 'Regular'),
('James Taylor', 'james.t@email.com', '555-0107', 'San Antonio', 'TX', 'USA', 'Premium'),
('Maria Garcia', 'maria.g@email.com', '555-0108', 'San Diego', 'CA', 'USA', 'Regular'),
('Robert Martinez', 'robert.m@email.com', '555-0109', 'Dallas', 'TX', 'USA', 'VIP'),
('Jennifer Lee', 'jennifer.l@email.com', '555-0110', 'San Jose', 'CA', 'USA', 'Premium');

-- Insert sample suppliers
INSERT INTO suppliers (supplier_name, contact_person, email, phone, city, country, rating) VALUES
('TechCorp Supplies', 'Alice Cooper', 'alice@techcorp.com', '555-1001', 'Seattle', 'USA', 4.5),
('Global Electronics', 'Bob Johnson', 'bob@globalelec.com', '555-1002', 'Austin', 'USA', 4.2),
('Premium Parts Ltd', 'Carol White', 'carol@premiumparts.com', '555-1003', 'Denver', 'USA', 4.8),
('Quality Components', 'Dan Brown', 'dan@qualitycomp.com', '555-1004', 'Portland', 'USA', 4.1),
('Reliable Suppliers', 'Eva Green', 'eva@reliable.com', '555-1005', 'Miami', 'USA', 4.6);

-- Insert sample products
INSERT INTO products (product_name, category, subcategory, brand, unit_price, cost_price, stock_quantity, supplier_id) VALUES
('Wireless Bluetooth Headphones', 'Electronics', 'Audio', 'SoundMax', 79.99, 45.00, 150, 1),
('Smartphone Case', 'Electronics', 'Accessories', 'ProtectPro', 24.99, 12.00, 300, 2),
('USB-C Charging Cable', 'Electronics', 'Cables', 'PowerLink', 19.99, 8.50, 500, 1),
('Portable Power Bank', 'Electronics', 'Power', 'ChargeUp', 49.99, 28.00, 200, 3),
('Wireless Mouse', 'Electronics', 'Computer', 'ClickTech', 34.99, 18.00, 180, 2),
('Laptop Stand', 'Electronics', 'Accessories', 'ErgoPro', 89.99, 52.00, 75, 4),
('LED Desk Lamp', 'Home & Office', 'Lighting', 'BrightLight', 59.99, 32.00, 120, 5),
('Coffee Mug', 'Home & Office', 'Kitchen', 'BrewMaster', 14.99, 6.50, 400, 5),
('Notebook Set', 'Office Supplies', 'Stationery', 'WriteWell', 12.99, 5.00, 250, 4),
('Ergonomic Keyboard', 'Electronics', 'Computer', 'TypeEase', 129.99, 75.00, 90, 3);

-- Insert sample orders (last 12 months)
INSERT INTO orders (customer_id, order_date, ship_date, delivery_date, order_status, total_amount, payment_method, region) VALUES
(1, '2024-01-15', '2024-01-16', '2024-01-18', 'Delivered', 159.98, 'Credit Card', 'Northeast'),
(2, '2024-01-20', '2024-01-21', '2024-01-23', 'Delivered', 44.98, 'PayPal', 'West'),
(3, '2024-02-05', '2024-02-06', '2024-02-08', 'Delivered', 89.99, 'Credit Card', 'Midwest'),
(4, '2024-02-12', '2024-02-13', '2024-02-15', 'Delivered', 79.99, 'Debit Card', 'South'),
(5, '2024-02-28', '2024-03-01', '2024-03-03', 'Delivered', 234.97, 'Credit Card', 'West'),
(6, '2024-03-10', '2024-03-11', '2024-03-13', 'Delivered', 74.98, 'PayPal', 'Northeast'),
(7, '2024-03-22', '2024-03-23', '2024-03-25', 'Delivered', 129.99, 'Credit Card', 'South'),
(8, '2024-04-05', '2024-04-06', '2024-04-08', 'Delivered', 94.98, 'Debit Card', 'West'),
(9, '2024-04-18', '2024-04-19', '2024-04-21', 'Delivered', 199.98, 'Credit Card', 'South'),
(10, '2024-05-02', '2024-05-03', '2024-05-05', 'Delivered', 64.98, 'PayPal', 'West'),
(1, '2024-05-15', '2024-05-16', '2024-05-18', 'Delivered', 149.98, 'Credit Card', 'Northeast'),
(3, '2024-06-01', '2024-06-02', '2024-06-04', 'Delivered', 179.98, 'Credit Card', 'Midwest'),
(5, '2024-06-20', '2024-06-21', '2024-06-23', 'Delivered', 289.97, 'Credit Card', 'West'),
(2, '2024-07-08', '2024-07-09', '2024-07-11', 'Delivered', 119.98, 'PayPal', 'West'),
(4, '2024-07-25', '2024-07-26', '2024-07-28', 'Delivered', 84.99, 'Debit Card', 'South'),
(7, '2024-08-10', '2024-08-11', NULL, 'Shipped', 159.98, 'Credit Card', 'South'),
(9, '2024-08-15', NULL, NULL, 'Processing', 224.97, 'Credit Card', 'South');

-- Insert sample order items
INSERT INTO order_items (order_id, product_id, quantity, unit_price, line_total) VALUES
-- Order 1
(1, 1, 2, 79.99, 159.98),
-- Order 2
(2, 2, 1, 24.99, 24.99),
(2, 3, 1, 19.99, 19.99),
-- Order 3
(3, 6, 1, 89.99, 89.99),
-- Order 4
(4, 1, 1, 79.99, 79.99),
-- Order 5
(5, 4, 2, 49.99, 99.98),
(5, 5, 1, 34.99, 34.99),
(5, 8, 1, 14.99, 14.99),
(5, 9, 2, 12.99, 25.98),
(5, 7, 1, 59.99, 59.99),
-- Order 6
(6, 2, 2, 24.99, 49.98),
(6, 3, 1, 19.99, 19.99),
-- Order 7
(7, 10, 1, 129.99, 129.99),
-- Order 8
(8, 1, 1, 79.99, 79.99),
(8, 8, 1, 14.99, 14.99),
-- Order 9
(9, 4, 2, 49.99, 99.98),
(9, 6, 1, 89.99, 89.99),
-- Order 10
(10, 2, 1, 24.99, 24.99),
(10, 3, 2, 19.99, 39.98),
-- Order 11
(11, 1, 1, 79.99, 79.99),
(11, 7, 1, 59.99, 59.99),
-- Order 12
(12, 4, 1, 49.99, 49.99),
(12, 10, 1, 129.99, 129.99),
-- Order 13
(13, 1, 2, 79.99, 159.98),
(13, 5, 1, 34.99, 34.99),
(13, 8, 2, 14.99, 29.98),
(13, 9, 2, 12.99, 25.98),
-- Order 14
(14, 2, 3, 24.99, 74.97),
(14, 3, 2, 19.99, 39.98),
-- Order 15
(15, 7, 1, 59.99, 59.99),
(15, 8, 1, 14.99, 14.99),
-- Order 16
(16, 1, 2, 79.99, 159.98),
-- Order 17
(17, 4, 2, 49.99, 99.98),
(17, 6, 1, 89.99, 89.99),
(17, 5, 1, 34.99, 34.99);

-- Create indexes for better performance
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_customers_segment ON customers(customer_segment);

-- Create a view for sales analysis
CREATE VIEW sales_summary AS
SELECT 
    o.order_id,
    o.order_date,
    c.customer_name,
    c.customer_segment,
    c.city,
    c.state,
    o.region,
    p.product_name,
    p.category,
    p.brand,
    oi.quantity,
    oi.unit_price,
    oi.line_total,
    o.total_amount as order_total
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id;

-- Insert some additional data for better analytics
INSERT INTO customers (customer_name, email, phone, city, state, country, customer_segment, registration_date) VALUES
('Alex Thompson', 'alex.t@email.com', '555-0111', 'Boston', 'MA', 'USA', 'Premium', '2023-06-15'),
('Rachel Green', 'rachel.g@email.com', '555-0112', 'Atlanta', 'GA', 'USA', 'VIP', '2023-08-20'),
('Tom Wilson', 'tom.w@email.com', '555-0113', 'Las Vegas', 'NV', 'USA', 'Regular', '2023-09-10'),
('Sophie Chen', 'sophie.c@email.com', '555-0114', 'San Francisco', 'CA', 'USA', 'Premium', '2023-11-05'),
('Mark Davis', 'mark.d@email.com', '555-0115', 'Orlando', 'FL', 'USA', 'Regular', '2024-01-12');

-- Add more recent orders for trend analysis
INSERT INTO orders (customer_id, order_date, ship_date, delivery_date, order_status, total_amount, payment_method, region) VALUES
(11, '2024-08-01', '2024-08-02', '2024-08-04', 'Delivered', 189.97, 'Credit Card', 'Northeast'),
(12, '2024-08-05', '2024-08-06', '2024-08-08', 'Delivered', 144.98, 'PayPal', 'South'),
(13, '2024-08-10', '2024-08-11', '2024-08-13', 'Delivered', 79.99, 'Debit Card', 'West'),
(14, '2024-08-12', '2024-08-13', '2024-08-15', 'Delivered', 259.96, 'Credit Card', 'West'),
(15, '2024-08-14', '2024-08-15', '2024-08-17', 'Delivered', 94.98, 'PayPal', 'South');

-- Add corresponding order items
INSERT INTO order_items (order_id, product_id, quantity, unit_price, line_total) VALUES
-- Order 18
(18, 1, 1, 79.99, 79.99),
(18, 4, 1, 49.99, 49.99),
(18, 7, 1, 59.99, 59.99),
-- Order 19
(19, 2, 2, 24.99, 49.98),
(19, 5, 1, 34.99, 34.99),
(19, 8, 4, 14.99, 59.96),
-- Order 20
(20, 1, 1, 79.99, 79.99),
-- Order 21
(21, 10, 2, 129.99, 259.98),
-- Order 22
(22, 3, 2, 19.99, 39.98),
(22, 6, 1, 89.99, 89.99);
