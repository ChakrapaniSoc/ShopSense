"""ShopSense FastAPI service. Stateless request handlers persist all live data in Postgres."""
from __future__ import annotations

import os
import uuid
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

import pandas as pd
import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from psycopg.rows import dict_row

from modules.analytics import calculate_metrics, segment_customers
from modules.automata import process_actions
from modules.pattern_mining import mine_patterns

ROOT = Path(__file__).parent
# Uvicorn does not load a project .env by default. Keep this server-side and
# preserve deployment-provided environment variables over local file values.
load_dotenv(ROOT / ".env", override=False)
app = FastAPI(title="ShopSense API", version="1.0.0", description="Live shopping events, analytics, and DFA journeys.")
frontend_origin = os.getenv("FRONTEND_ORIGIN")
if frontend_origin:
    app.add_middleware(CORSMiddleware, allow_origins=[frontend_origin], allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
Action = Literal["Browse", "View Product", "Add to Cart", "Remove from Cart", "Checkout", "Abandon"]

class EventInput(BaseModel):
    session_id: str = Field(min_length=8, max_length=80)
    customer_id: str = Field(min_length=8, max_length=80)
    device_type: str = Field(default="Unknown", max_length=40)
    action: Action
    product_id: str | None = Field(default=None, max_length=80)
    quantity: int = Field(default=1, ge=1, le=20)

class CartItem(BaseModel):
    product_id: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=1, le=20)

class CheckoutInput(BaseModel):
    session_id: str = Field(min_length=8, max_length=80)
    customer_id: str = Field(min_length=8, max_length=80)
    device_type: str = Field(default="Unknown", max_length=40)
    items: list[CartItem] = Field(min_length=1, max_length=30)

def open_database():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="Database is not configured. Set DATABASE_URL to a hosted PostgreSQL connection string.")
    if "YOUR_SUPABASE" in url or "YOUR_" in url or "CHANGE_ME" in url:
        raise HTTPException(status_code=503, detail="DATABASE_URL still contains the example placeholder. Set it to your Supabase PostgreSQL connection string in the project-root .env.")
    try:
        return psycopg.connect(url, connect_timeout=5, prepare_threshold=None, row_factory=dict_row)
    except psycopg.Error as exc:
        # Do not chain driver exceptions: some libpq errors include connection details.
        raise HTTPException(status_code=503, detail="Could not connect to PostgreSQL. Check the Supabase connection settings and network access.") from None

@contextmanager
def database():
    conn = open_database()
    try:
        with conn:
            yield conn
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="PostgreSQL request failed. Verify the schema migration and connection settings.") from None
    finally:
        conn.close()

def touch_session(conn, session_id: str, customer_id: str, device_type: str):
    conn.execute("""INSERT INTO shopping_sessions(id, customer_id, device_type) VALUES (%s,%s,%s)
        ON CONFLICT (id) DO UPDATE SET updated_at=NOW(), device_type=EXCLUDED.device_type""",
        (session_id, customer_id, device_type or "Unknown"))

def add_event(conn, session_id: str, action: str, product_id: str | None = None, quantity: int = 1):
    conn.execute("INSERT INTO session_events(session_id, action, product_id, quantity) VALUES (%s,%s,%s,%s)",
                 (session_id, action, product_id, quantity))
    conn.execute("UPDATE shopping_sessions SET updated_at=NOW() WHERE id=%s", (session_id,))

@app.get("/api/health")
def health():
    with database() as conn:
        conn.execute("SELECT 1")
    return {"ok": True, "database": "connected"}

@app.get("/api/products")
def products(category: str | None = None, search: str | None = None):
    query = "SELECT id, name, category, description, price::float AS price, image_url, featured FROM products"
    clauses, params = [], []
    if category and category != "All": clauses.append("category=%s"); params.append(category)
    if search:
        clauses.append("(name ILIKE %s OR category ILIKE %s OR description ILIKE %s)")
        needle = f"%{search}%"; params.extend([needle, needle, needle])
    if clauses: query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY featured DESC, name"
    with database() as conn:
        return conn.execute(query, params).fetchall()

@app.post("/api/events", status_code=201)
def create_event(event: EventInput):
    with database() as conn:
        touch_session(conn, event.session_id, event.customer_id, event.device_type)
        add_event(conn, event.session_id, event.action, event.product_id, event.quantity)
        row = conn.execute("SELECT id, action, product_id, quantity, created_at FROM session_events WHERE id=currval(pg_get_serial_sequence('session_events','id'))").fetchone()
    return row

@app.post("/api/checkout", status_code=201)
def checkout(payload: CheckoutInput):
    purchase_id = uuid.uuid4()
    with database() as conn:
        touch_session(conn, payload.session_id, payload.customer_id, payload.device_type)
        product_ids = list(dict.fromkeys(item.product_id for item in payload.items))
        rows = conn.execute("SELECT id, name, price::float AS price FROM products WHERE id=ANY(%s)", (product_ids,)).fetchall()
        products_by_id = {row["id"]: row for row in rows}
        if len(products_by_id) != len(product_ids): raise HTTPException(status_code=400, detail="Your cart contains a product that is no longer available.")
        total = round(sum(products_by_id[item.product_id]["price"] * item.quantity for item in payload.items), 2)
        conn.execute("INSERT INTO purchases(id, session_id, total) VALUES (%s,%s,%s)", (purchase_id, payload.session_id, total))
        for item in payload.items:
            conn.execute("INSERT INTO purchase_items(purchase_id, product_id, quantity, unit_price) VALUES (%s,%s,%s,%s)",
                         (purchase_id, item.product_id, item.quantity, products_by_id[item.product_id]["price"]))
        add_event(conn, payload.session_id, "Purchase")
    return {"purchase_id": str(purchase_id), "session_id": payload.session_id, "total": total,
            "message": "Demo order confirmed. No payment details were collected."}

def load_live_frame(conn):
    rows = conn.execute("""SELECT s.id AS session_id, s.customer_id, s.device_type, s.created_at AS timestamp,
        e.id AS event_id, e.action, e.product_id, e.quantity, e.created_at AS event_time, p.category
        FROM shopping_sessions s LEFT JOIN session_events e ON e.session_id=s.id
        LEFT JOIN products p ON p.id=e.product_id ORDER BY s.updated_at DESC, e.id""").fetchall()
    grouped: dict[str, dict] = {}
    for row in rows:
        sid = row["session_id"]
        rec = grouped.setdefault(sid, {"session_id":sid,"customer_id":row["customer_id"],"device_type":row["device_type"],"timestamp":row["timestamp"],"actions":[],"items_viewed":0,"items_added_to_cart":0,"checkout_started":False,"purchase_completed":False,"session_duration_seconds":0,"total_purchase_amount":0.0,"product_category":"Unknown","product_basket":[],"_first_event":None,"_last_event":None})
        if row["event_id"] is None: continue
        action = row["action"]; rec["actions"].append(action)
        rec["_first_event"] = row["event_time"] if rec["_first_event"] is None else rec["_first_event"]
        rec["_last_event"] = row["event_time"]
        if action == "View Product": rec["items_viewed"] += 1
        if action == "Add to Cart": rec["items_added_to_cart"] += int(row["quantity"])
        if action == "Checkout": rec["checkout_started"] = True
        if action == "Purchase": rec["purchase_completed"] = True
        if row["category"]:
            rec["product_category"] = row["category"]
            if action == "Purchase" and row["category"] not in rec["product_basket"]: rec["product_basket"].append(row["category"])
    purchase_rows = conn.execute("""SELECT pu.session_id, pu.total::float AS total,
        array_agg(DISTINCT pr.category) AS categories FROM purchases pu
        JOIN purchase_items pi ON pi.purchase_id=pu.id JOIN products pr ON pr.id=pi.product_id
        GROUP BY pu.id, pu.session_id, pu.total""").fetchall()
    for row in purchase_rows:
        if row["session_id"] in grouped:
            rec = grouped[row["session_id"]]; rec["total_purchase_amount"] += row["total"]
            for category in row["categories"] or []:
                if category not in rec["product_basket"]: rec["product_basket"].append(category)
    for rec in grouped.values():
        if rec["_first_event"] and rec["_last_event"]:
            rec["session_duration_seconds"] = max(0, int((rec["_last_event"]-rec["_first_event"]).total_seconds()))
        rec.pop("_first_event", None); rec.pop("_last_event", None)
    return pd.DataFrame(grouped.values()), rows

@app.get("/api/dashboard")
def dashboard():
    with database() as conn:
        frame, _ = load_live_frame(conn)
        metrics = calculate_metrics(frame) if not frame.empty else {"total_sessions":0,"unique_customers":0,"purchases":0,"conversion_rate":0.0,"cart_abandonment_rate":0.0,"checkout_abandonment_rate":0.0,"average_session_duration":0.0,"average_order_value":0.0,"revenue_by_category":pd.Series(dtype=float),"conversion_by_device":pd.Series(dtype=float),"popular_actions":pd.Series(dtype=int),"common_sequences":pd.Series(dtype=int)}
        category_revenue = conn.execute("""SELECT pr.category AS name, SUM(pi.unit_price*pi.quantity)::float AS value
            FROM purchase_items pi JOIN products pr ON pr.id=pi.product_id GROUP BY pr.category ORDER BY value DESC""").fetchall()
        metrics["revenue_by_category"] = pd.Series({row["name"]:row["value"] for row in category_revenue},dtype=float)
        funnel = [{"stage":"Sessions","value":int(len(frame))}]
        funnel.extend([{"stage":"Viewed product","value":int(frame.items_viewed.gt(0).sum()) if not frame.empty else 0},{"stage":"Added to cart","value":int(frame.items_added_to_cart.gt(0).sum()) if not frame.empty else 0},{"stage":"Checkout","value":int(frame.checkout_started.sum()) if not frame.empty else 0},{"stage":"Purchased","value":int(frame.purchase_completed.sum()) if not frame.empty else 0}])
        feed = conn.execute("""SELECT e.id, e.session_id, e.action, e.product_id, p.name AS product_name,
            e.quantity, e.created_at FROM session_events e LEFT JOIN products p ON p.id=e.product_id
            ORDER BY e.id DESC LIMIT 18""").fetchall()
    return {"source":"live_postgres","metrics":{k:(v if not isinstance(v,pd.Series) else [{"name":str(i),"value":float(x)} for i,x in v.items()]) for k,v in metrics.items()},
            "funnel":funnel,"event_feed":feed}

@app.get("/api/journeys")
def journeys(limit: int = Query(default=12, ge=1, le=100)):
    with database() as conn:
        frame, _ = load_live_frame(conn)
    if frame.empty: return []
    frame = frame.sort_values("timestamp", ascending=False).head(limit)
    return [{"session_id":row.session_id,"customer_id":row.customer_id,"device_type":row.device_type,
             "timestamp":row.timestamp.isoformat() if hasattr(row.timestamp,"isoformat") else str(row.timestamp),
             "actions":row.actions,"dfa":process_actions(row.actions).__dict__} for row in frame.itertuples()]

@app.get("/api/segments")
def segments(clusters: int = Query(default=4, ge=2, le=8)):
    with database() as conn: frame, _ = load_live_frame(conn)
    if frame.empty: return {"error":"No live shopping sessions yet.","customers":[],"summary":[]}
    customers, summary, error = segment_customers(frame, clusters)
    if error: return {"error":error,"customers":[],"summary":[]}
    return {"error":None,"customers":customers.reset_index().to_dict(orient="records"),"summary":summary.reset_index().to_dict(orient="records")}

@app.get("/api/patterns")
def patterns(min_support: float = Query(default=0.08, gt=0, le=1), min_confidence: float = Query(default=0.3, ge=0, le=1)):
    with database() as conn:
        baskets = conn.execute("""SELECT pu.id, string_agg(DISTINCT pr.category, '|' ORDER BY pr.category) AS categories
            FROM purchases pu JOIN purchase_items pi ON pi.purchase_id=pu.id JOIN products pr ON pr.id=pi.product_id GROUP BY pu.id""").fetchall()
    if not baskets: return {"error":"No completed live purchases yet.","rules":[]}
    frame = pd.DataFrame([{"purchase_completed":True,"product_category":row["categories"] or "","product_basket":json.dumps((row["categories"] or "").split("|"))} for row in baskets])
    rules, error = mine_patterns(frame,min_support,min_confidence)
    if error: return {"error":error,"rules":[]}
    return {"error":None,"rules":rules[["antecedents","consequents","support","confidence","lift"]].to_dict(orient="records")}

@app.get("/api/automata")
def automata(session_id: str | None = None):
    with database() as conn:
        if session_id:
            actions = conn.execute("SELECT action FROM session_events WHERE session_id=%s ORDER BY id",(session_id,)).fetchall()
        else:
            recent = conn.execute("SELECT id FROM shopping_sessions ORDER BY updated_at DESC LIMIT 1").fetchone()
            actions = conn.execute("SELECT action FROM session_events WHERE session_id=%s ORDER BY id",(recent["id"],)).fetchall() if recent else []
    result = process_actions([row["action"] for row in actions])
    return result.__dict__

@app.get("/api/{path:path}")
def unknown_api(path: str):
    raise HTTPException(status_code=404, detail="API route not found.")

dist = ROOT / "dist"
if dist.exists():
    if os.getenv("VERCEL") and hasattr(app, "frontend"):
        app.frontend("/", directory=str(dist), fallback="index.html")
    else:
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
