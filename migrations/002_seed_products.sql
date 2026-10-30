-- ShopSense storefront catalogue seed. Safe to run repeatedly; preserves the existing schema.
INSERT INTO products (id, name, category, description, price, image_url, featured) VALUES
('arc-ceramic-vase', 'Arc Ceramic Vase', 'Home Decor', 'Sculptural stoneware with a softly curved profile and a matte, sand-colored glaze.', 2890.00, 'https://images.unsplash.com/photo-1578500494198-246f612d3b3d?auto=format&fit=crop&w=1000&q=85', TRUE),
('woven-wall-basket', 'Woven Wall Basket Set', 'Home Decor', 'A set of three handwoven natural-fiber baskets for a warm, layered wall display.', 3450.00, 'https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1000&q=85', FALSE),
('terracotta-planter', 'Terra Footed Planter', 'Home Decor', 'A sturdy terracotta planter raised on a low foot, made for leafy indoor plants.', 1950.00, 'https://images.unsplash.com/photo-1485955900006-10f4d324d411?auto=format&fit=crop&w=1000&q=85', FALSE),
('linen-cushion-cover', 'Washed Linen Cushion Cover', 'Home Decor', 'Breathable European flax linen in a relaxed natural shade with concealed closure.', 1650.00, 'https://images.unsplash.com/photo-1584100936595-c0654b55a2e2?auto=format&fit=crop&w=1000&q=85', FALSE),
('brass-table-lamp', 'Brass Stem Table Lamp', 'Lighting', 'A compact brushed-brass lamp with a linen shade for a gentle evening glow.', 6490.00, 'https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=1000&q=85', TRUE),
('opal-globe-pendant', 'Opal Globe Pendant', 'Lighting', 'A clean opal glass globe pendant with warm metal detailing for intimate rooms.', 8250.00, 'https://images.unsplash.com/photo-1543198126-a8ad8e47fb22?auto=format&fit=crop&w=1000&q=85', FALSE),
('portable-reading-light', 'Rechargeable Reading Light', 'Lighting', 'A portable dimmable lamp with a warm LED, made for bedside tables and reading nooks.', 3790.00, 'https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=1000&q=85', FALSE),
('stoneware-dinner-set', 'Everyday Stoneware Dinner Set', 'Kitchen and Dining', 'Four dinner plates and four side plates in durable, speckled glazed stoneware.', 5890.00, 'https://images.unsplash.com/photo-1603199506016-b9a594b593c0?auto=format&fit=crop&w=1000&q=85', TRUE),
('fluted-glass-set', 'Fluted Water Glasses', 'Kitchen and Dining', 'A set of four clear fluted tumblers that feel considered in everyday use.', 1490.00, 'https://images.unsplash.com/photo-1513558161293-cdaf765edfd7?auto=format&fit=crop&w=1000&q=85', FALSE),
('oak-serving-board', 'Oak Serving Board', 'Kitchen and Dining', 'Solid oiled oak board with a rounded handle for serving bread, fruit, and cheese.', 2250.00, 'https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=1000&q=85', FALSE),
('cotton-table-runner', 'Textured Cotton Table Runner', 'Kitchen and Dining', 'A softly textured cotton runner, woven in a neutral palette for everyday tables.', 1790.00, 'https://images.unsplash.com/photo-1603199506016-b9a594b593c0?auto=format&fit=crop&w=1000&q=85', FALSE),
('round-side-table', 'Solid Oak Side Table', 'Furniture', 'A compact solid-oak side table with rounded edges and a considered, sturdy stance.', 11900.00, 'https://images.unsplash.com/photo-1499933374294-4584851497cc?auto=format&fit=crop&w=1000&q=85', TRUE),
('cane-lounge-chair', 'Cane and Ash Lounge Chair', 'Furniture', 'An ash wood frame and handwoven cane seat create an airy place to settle in.', 24900.00, 'https://images.unsplash.com/photo-1598300056393-4aac492f4344?auto=format&fit=crop&w=1000&q=85', FALSE),
('modular-bookshelf', 'Modular Oak Book Shelf', 'Furniture', 'A versatile open shelf in oak veneer for books, keepsakes, and useful objects.', 18900.00, 'https://images.unsplash.com/photo-1594620302200-9a762244a156?auto=format&fit=crop&w=1000&q=85', FALSE),
('leather-everyday-tote', 'Everyday Leather Tote', 'Lifestyle Accessories', 'A roomy carryall in supple leather with a simple silhouette for daily errands.', 7850.00, 'https://images.unsplash.com/photo-1590874103328-eac38a683ce7?auto=format&fit=crop&w=1000&q=85', TRUE),
('journal-and-pencil-set', 'Cloth Journal and Pencil Set', 'Lifestyle Accessories', 'A cloth-bound notebook paired with a cedar pencil for notes on the move.', 1250.00, 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&w=1000&q=85', FALSE)
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  category = EXCLUDED.category,
  description = EXCLUDED.description,
  price = EXCLUDED.price,
  image_url = EXCLUDED.image_url,
  featured = EXCLUDED.featured;
