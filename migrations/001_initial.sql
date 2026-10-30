-- ShopSense production schema. Run with psql or paste into the hosted Postgres SQL editor.
CREATE TABLE IF NOT EXISTS products (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  price NUMERIC(12, 2) NOT NULL CHECK (price >= 0),
  image_url TEXT NOT NULL,
  featured BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS shopping_sessions (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  device_type TEXT NOT NULL DEFAULT 'Unknown',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS session_events (
  id BIGSERIAL PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES shopping_sessions(id) ON DELETE CASCADE,
  action TEXT NOT NULL CHECK (action IN ('Browse', 'View Product', 'Add to Cart', 'Remove from Cart', 'Checkout', 'Purchase', 'Abandon')),
  product_id TEXT REFERENCES products(id),
  quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS purchases (
  id UUID PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES shopping_sessions(id),
  total NUMERIC(12, 2) NOT NULL CHECK (total >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS purchase_items (
  id BIGSERIAL PRIMARY KEY,
  purchase_id UUID NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
  product_id TEXT NOT NULL REFERENCES products(id),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0)
);

CREATE INDEX IF NOT EXISTS idx_events_session_order ON session_events(session_id, id);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON session_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_purchases_session ON purchases(session_id);

INSERT INTO products (id, name, category, description, price, image_url, featured) VALUES
('linen-shirt', 'The Everyday Linen Shirt', 'Clothing', 'Relaxed European linen, made for slow mornings and long afternoons.', 3890, 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=1000&q=85', TRUE),
('ceramic-vase', 'Sculpted Stoneware Vase', 'Home', 'Hand-finished stoneware with a soft, chalky glaze.', 2450, 'https://images.unsplash.com/photo-1578500494198-246f612d3b3d?auto=format&fit=crop&w=1000&q=85', TRUE),
('leather-tote', 'Studio Leather Tote', 'Accessories', 'A considered everyday carryall in supple, responsibly sourced leather.', 7250, 'https://images.unsplash.com/photo-1590874103328-eac38a683ce7?auto=format&fit=crop&w=1000&q=85', TRUE),
('journal-set', 'The Daily Journal Set', 'Stationery', 'Two cloth-bound notebooks for thoughts worth keeping.', 980, 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&w=1000&q=85', FALSE),
('ribbed-mug', 'Ribbed Morning Mug', 'Home', 'A tactile ceramic mug, balanced in the hand and made for daily use.', 1250, 'https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?auto=format&fit=crop&w=1000&q=85', FALSE),
('cotton-throw', 'Woven Cotton Throw', 'Home', 'A soft, breathable layer woven in a warm natural palette.', 4200, 'https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1000&q=85', FALSE),
('sandalwood-candle', 'Sandalwood No. 04 Candle', 'Objects', 'A quiet, grounding blend poured in a reusable glass vessel.', 1680, 'https://images.unsplash.com/photo-1603006905003-be475563bc59?auto=format&fit=crop&w=1000&q=85', FALSE),
('silver-hoops', 'Form Silver Hoops', 'Accessories', 'Lightweight sculptural hoops in recycled sterling silver.', 3150, 'https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?auto=format&fit=crop&w=1000&q=85', TRUE)
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, category = EXCLUDED.category,
  description = EXCLUDED.description, price = EXCLUDED.price, image_url = EXCLUDED.image_url,
  featured = EXCLUDED.featured;
