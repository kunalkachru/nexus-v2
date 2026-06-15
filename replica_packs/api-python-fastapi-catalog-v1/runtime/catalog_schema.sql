-- Catalog database schema for query regression replay
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product_facets (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    facet_key VARCHAR(100),
    facet_value VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_name ON products(name);
CREATE INDEX idx_facets_product ON product_facets(product_id);
CREATE INDEX idx_facets_key_value ON product_facets(facet_key, facet_value);

-- Sample data
INSERT INTO products (name, description, price) VALUES
  ('Test Product 1', 'A test product', 99.99),
  ('Test Product 2', 'Another test product', 149.99)
ON CONFLICT DO NOTHING;
