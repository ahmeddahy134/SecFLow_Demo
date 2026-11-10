-- Database initialization script for E-commerce Store (SecFlow Demo)
-- Production tables are created via SQLAlchemy models in app/models.py
-- This script safely ensures necessary extensions and base schema exist.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Sample products seed data (public product catalog)
INSERT INTO products (id, name, description, price, category, image_url, stock, rating, created_at, updated_at) VALUES
('prod-001', 'Wireless Headphones', 'High-quality wireless headphones with noise cancellation', 99.99, 'Electronics', 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500', 50, 4.5, NOW(), NOW()),
('prod-002', 'Smart Watch', 'Fitness tracking smartwatch with heart rate monitor', 199.99, 'Electronics', 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500', 30, 4.2, NOW(), NOW()),
('prod-003', 'Canvas Backpack', 'Durable canvas backpack for travel and daily adventures', 45.99, 'Clothing', 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500', 25, 4.0, NOW(), NOW()),
('prod-004', 'Running Shoes', 'Comfortable running shoes with excellent cushioning', 129.99, 'Sports', 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500', 40, 4.3, NOW(), NOW()),
('prod-005', 'Coffee Maker', 'Automatic coffee maker with programmable features', 79.99, 'Home & Garden', 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=500', 15, 4.1, NOW(), NOW()),
('prod-006', 'Bluetooth Speaker', 'Portable Bluetooth speaker with 360-degree sound', 59.99, 'Electronics', 'https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=500', 35, 4.4, NOW(), NOW()),
('prod-007', 'Yoga Mat', 'Non-slip yoga mat for home workouts', 29.99, 'Sports', 'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=500', 60, 4.0, NOW(), NOW()),
('prod-008', 'Laptop Stand', 'Adjustable laptop stand for better ergonomics', 39.99, 'Electronics', 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=500', 20, 4.2, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;
