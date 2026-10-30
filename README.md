# ShopSense

ShopSense is a small full-stack commerce demo and analytics studio. The editorial storefront writes each visit, product view, cart action, and simulated checkout to hosted PostgreSQL. A dark analytics workspace polls those persisted records and replays each session through the project's original DFA.

The prior Streamlit project is preserved in [`backup/streamlit-original/`](backup/streamlit-original/). The live storefront and demo data are separate: the live dashboard never falls back to synthetic metrics.

## Migration plan and reuse

- `modules/automata.py` remains the source of truth for action order, transitions, histories, and classifications.
- `modules/analytics.py` provides live session metrics and scaled customer segmentation.
- `modules/pattern_mining.py` runs Apriori on persisted purchase baskets.
- `data/generate_data.py`, the original Streamlit `app.py`, CSV, tests, and README are preserved in the backup.
- `main.py` is a stateless FastAPI service. It opens a short PostgreSQL connection per request; it has no local database or in-memory event store.
- `src/` is a Vite React/TypeScript single-page app. Same-origin `/api/*` calls work locally through Vite's proxy and on Vercel through its FastAPI runtime.

## Features

- Product search and category filters, product views, cart edits, and a simulated purchase checkout that takes no payment details.
- PostgreSQL records for products, anonymous browser sessions, ordered session events, purchases, and purchase line items.
- Analytics sourced from persisted live rows: conversion, abandonment, revenue, device conversion, event feed, shopping funnel, and session DFA replay.
- Customer segments and association rules calculated from live sessions and completed purchase baskets.
- Responsive cream storefront and a separate dark analytics workspace.
- Synthetic session generator and the previous Streamlit app retained as a separate educational demo.

## Project structure

```text
shopsense/
├── main.py                    # FastAPI app and Vercel entrypoint
├── src/                       # React + TypeScript storefront and analytics
├── migrations/001_initial.sql # PostgreSQL tables, indexes, and original starter products
├── migrations/002_seed_products.sql # repeatable 16-product storefront catalogue seed
├── modules/                   # reused DFA, analytics, and Apriori logic
├── data/                      # separate synthetic demo generator and CSV
├── tests/                     # original unit tests plus backend API checks
├── backup/streamlit-original/ # preserved Streamlit project snapshot
├── package.json               # Vite / React toolchain
├── package-lock.json          # reproducible frontend install
├── requirements.txt           # FastAPI and reused Python algorithms
├── pyproject.toml             # Vercel Python entrypoint and build command
└── vercel.json                # function limits and bundle exclusions
```

## Local development

Prerequisites: Python 3.11+, Node.js 20+, npm, and a hosted PostgreSQL database (or a local PostgreSQL server for development). There is intentionally no SQLite fallback.

1. Create a database on Supabase, Neon, or another PostgreSQL provider.
2. Apply `migrations/001_initial.sql` once using the Supabase SQL Editor. This creates the existing schema (including `products`, `shopping_sessions`, and `session_events`) and includes its original starter catalogue. Then run `migrations/002_seed_products.sql` in the same SQL Editor to add/update the 16 item ShopSense catalogue. The seed uses `ON CONFLICT (id) DO UPDATE`, so it is safe to rerun and does not create or alter tables. To use `psql` instead:

   ```powershell
   psql "$env:DATABASE_URL" -f migrations/001_initial.sql
   psql "$env:DATABASE_URL" -f migrations/002_seed_products.sql
   ```

3. Copy `.env.example` to the project-root `.env` if needed and set `DATABASE_URL` to the connection URI copied from Supabase. Use its Session Pooler URI for local development; for Vercel serverless functions, use the Transaction Pooler URI. The FastAPI driver disables prepared statements for compatibility with transaction pooling. FastAPI loads this root `.env` at startup; values already supplied by the shell or deployment environment take precedence. Keep the password private. Alternatively, set the value in the shell (PowerShell example):

   ```powershell
   $env:DATABASE_URL = "postgresql://..."
   ```

   `DATABASE_URL` is read only by FastAPI. Do not put it in a `VITE_` variable or browser code.

4. Install the Python requirements and frontend packages:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   npm install
   ```

5. Start the API and Vite in two terminals:

   ```powershell
   uvicorn main:app --reload --host 127.0.0.1 --port 8001
   npm run dev
   ```

   Open `http://localhost:5174`. Vite proxies `/api` to `http://127.0.0.1:8001`; the frontend calls `/api/products` and does not access the database directly. Port 8000 may be used by another local project, so ShopSense uses 8001 for local development. To use a separately hosted API, set `VITE_API_BASE_URL` at frontend build time and set `FRONTEND_ORIGIN` on the API host to the exact browser origin.

## Vercel deployment

This uses Vercel's Python FastAPI framework support with the app at `main.py`. The Vercel build command installs and builds the Vite app; FastAPI serves the compiled `dist/` UI and handles `/api/*`. Each request is a short serverless function invocation. There is no background process, websocket requirement, SQLite file, or assumption that process memory survives between requests. Dashboard refresh uses a five-second HTTP poll.

1. Create a hosted PostgreSQL project and apply `migrations/001_initial.sql` once, followed by `migrations/002_seed_products.sql`.
2. Push the project to a Git provider and import it into Vercel. Keep the project root at this repository root; do not set `src/` or `api/` as the Vercel root.
3. In **Project → Settings → Environment Variables**, add `DATABASE_URL` for Production, Preview, and Development as appropriate. Use the provider's pooled/serverless connection URI. Do not name it `VITE_DATABASE_URL` and do not expose it to the browser.
4. Leave `VITE_API_BASE_URL` unset for this same-origin deployment. If a separate API host is used, set `VITE_API_BASE_URL` before the Vite build and configure `FRONTEND_ORIGIN` on the API to the exact frontend origin.
5. Deploy. Check `/api/health`, then browse a product, add it to the bag, and complete a demo checkout. The dashboard should reflect those persisted events after its next poll.

Vercel functions are request-driven and have duration/resource limits; they are not a continuously running ASGI server. The app therefore creates a database connection per request and does not keep a worker, stream, or in-memory event queue alive. `vercel.json` limits function duration and excludes the backup, tests, generator data, and local virtual environment from the backend bundle.

### Environment variables

| Variable | Where | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | FastAPI runtime only | Hosted PostgreSQL URI, ideally the provider's pooled/serverless URI. Required for live products, event capture, purchases, and analytics. |
| `VITE_API_BASE_URL` | Vite build only | Optional API origin. Leave blank for same-origin `/api` routing. Never put secrets here. |
| `FRONTEND_ORIGIN` | FastAPI runtime only | Optional exact origin allowed by CORS if frontend and API use separate hosts. |
| `VERCEL` | Set by Vercel | Enables Vercel's built frontend integration when available. |

Do not commit `.env`. `.env.example` contains placeholders only. PostgreSQL credentials are read only by Python and never returned by the API.

### Hosted PostgreSQL options

- **Supabase Free** is a practical starter for a college demo. It provides hosted PostgreSQL and a standard connection URI; free projects can pause after a week with little activity, so the first request after a pause may need a wake-up delay. Its usage/storage quotas are limited and can change; check the current provider plan before publishing.
- **Neon Free** is another PostgreSQL option, with scale-to-zero after inactivity and current free quotas for compute, storage, and transfer. That makes it useful for low-traffic demos, with a cold-start on a sleeping database. Confirm the live plan limits and connect using the URI shown in the console.

Neither provider requires a paid plan to start. Supabase currently lists up to two free projects and warns that low-activity projects can pause. Neon currently lists 100 compute-hours and 1 GB storage per free project, and scales a compute endpoint to zero after five inactive minutes. Limits can change; check [Supabase's free-plan notes](https://supabase.com/kb/faqs/platform/free-postgres-for-side-projects) and [Neon's live plan table](https://neon.com/docs/introduction/plans) before publishing. Free-tier limits are not an uptime guarantee. Vercel's function runtime and database are separate services; the database remains the durable source of truth.

## Database and migrations

`migrations/001_initial.sql` creates:

- `products`: seeded storefront catalogue.
- `shopping_sessions`: anonymous customer/session identifiers and device type.
- `session_events`: append-only ordered action log with product, quantity, and timestamp.
- `purchases` and `purchase_items`: simulated order records and prices at purchase time.

The `products` columns are `id TEXT PRIMARY KEY`, `name TEXT NOT NULL`, `category TEXT NOT NULL`, `description TEXT NOT NULL DEFAULT ''`, `price NUMERIC(12,2) NOT NULL CHECK (price >= 0)`, `image_url TEXT NOT NULL`, `featured BOOLEAN NOT NULL DEFAULT FALSE`, and `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`. FastAPI's `GET /api/products` selects the seven storefront fields from this table, and React in `src/App.tsx` loads them from `/api/products` on startup. Categories and prices are display data; prices are in INR.

The event table's increasing ID orders actions within a session. The React storefront posts `Browse`, `View Product`, `Add to Cart`, and cart removal actions to `POST /api/events`. FastAPI upserts the browser's `shopping_sessions` row and inserts each event in the same request transaction. Checkout sends `Checkout` first, then `POST /api/checkout` creates the simulated purchase, line items, and `Purchase` event transactionally. The analytics dashboard reads the database-backed `/api/dashboard` and `/api/journeys` endpoints and polls them every five seconds. No synthetic data is used by these live endpoints. Product seed inserts are repeatable. No migration runner mutates the database at application startup.

For an already-migrated project whose `products` table exists but is empty, run **only `migrations/002_seed_products.sql`** in Supabase's SQL Editor. To verify, run `SELECT id, name, category, price, featured FROM products ORDER BY name;` and confirm at least 16 catalogue rows (the original 8 plus 16 seeded rows, subject to any prior rows). Then open `https://<your-api-host>/api/products` or visit the local Vite storefront with FastAPI configured; the endpoint should return those same rows. Check `/api/health` for database connectivity. Browse, view a product, add it to the bag, and complete checkout; `/api/dashboard` and the dashboard's event feed should reflect persisted actions on its next five-second poll. The SQL files can create/update rows, but this repository has not been connected to your Supabase project from this environment.

### UI components

`components.json` follows shadcn's Vite setup and registers Vibra's `@vibra` registry namespace, as described in the [Vibra installation guide](https://vibraui.com/docs/installation). The local `src/components/ui/card.tsx` is a source-owned shadcn-style primitive; `stat-card.tsx` adapts Vibra's free Stat Card composition and API to ShopSense's dark theme. Additional Vibra items can be copied through the documented CLI flow (`npx shadcn@latest add @vibra/<component>`), then edited locally.

## Tests and builds

```powershell
python -m unittest discover -s tests -v
python -m compileall -q main.py modules tests
npm run build
```

The original tests remain. API tests cover unavailable-database responses, product query behavior, and the session/event write path using a mocked database connection. A real insert/read/checkout integration test requires a configured `DATABASE_URL` and a PostgreSQL database with the migration applied; no live database credentials are committed.

## Synthetic educational demo

The bundled `data/shopping_data.csv` is synthetic and belongs to the previous Streamlit teaching demo. It is not seeded into PostgreSQL and is not read by the live API. Start the old application from the preserved snapshot in an environment with its original dependencies:

```powershell
cd backup\streamlit-original
streamlit run app.py
```

It retains the DFA simulator, original charts, KMeans clustering, and synthetic Apriori examples. The React analytics workspace uses live database events only.

## Architecture and limits

```text
React storefront ── POST /api/events ──┐
React analytics  ── GET  /api/* ────────┼── FastAPI serverless function ── Hosted PostgreSQL
Vite dev proxy / Vercel same origin ────┘             │
                                            modules/ automata + analytics + patterns
```

The app is an anonymous, public teaching demo: it has no user accounts, admin authorization, inventory reservation, tax/shipping calculation, payment collection, or production abuse controls. Session identifiers live in browser storage. Add authentication, rate limiting, consent/privacy controls, backups, and inventory/order safeguards before adapting it for a real store. Remote product photography requires a network connection. The DFA intentionally models a simplified purchase flow.

## Viva notes

- **DFA:** a finite-state machine that reads each stored action and follows one deterministic transition.
- **State:** the summarized progress of a shopping session (start, viewed, cart, checkout, purchase, abandonment, or invalid).
- **Alphabet:** the allowed shopping action symbols.
- **Transition function:** a rule from current state plus action to the next state.
- **Accepting state:** S4, reached after checkout then purchase. A browsed or abandoned session is not mislabeled as an invalid sequence.
- **KMeans:** groups customer-level numeric features after scaling; cluster IDs themselves have no meaning.
- **Association rule mining:** finds co-occurring product categories. Support is prevalence, confidence is conditional frequency, and lift compares against baseline frequency; it does not prove causation.
- **Why PostgreSQL?** Events and purchases must survive serverless function shutdowns and be shared by storefront and dashboard requests.
