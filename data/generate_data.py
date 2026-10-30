"""Create reproducible, explicitly synthetic session data."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

OUT = Path(__file__).with_name("shopping_data.csv")
PRODUCTS = ["Electronics", "Books", "Home", "Fashion", "Sports", "Beauty"]
BASES = {"Electronics": 5000, "Books": 650, "Home": 1800, "Fashion": 1400, "Sports": 1100, "Beauty": 800}

def generate_sessions(n=1200, seed=42):
    rng = np.random.default_rng(seed); rows = []; customers = 360
    for i in range(n):
        category = str(rng.choice(PRODUCTS)); customer = f"C{rng.integers(1, customers+1):04d}"
        outcome = rng.choice(["browse", "cart", "checkout", "purchase"], p=[.24,.29,.16,.31])
        views = int(rng.integers(1, 7)); actions = ["Browse"] + ["View Product"] * views
        added = int(rng.integers(1, 4)) if outcome != "browse" else 0
        if added: actions += ["Add to Cart"] * added
        if outcome == "cart" and rng.random() < .18: actions += ["Remove from Cart"]
        if outcome in ("checkout", "purchase"): actions += ["Checkout"]
        bought = outcome == "purchase"; checkout = outcome in ("checkout", "purchase")
        if bought: actions += ["Purchase"]
        elif rng.random() < .24: actions += ["Abandon"]
        items = int(rng.integers(1, 4)) if bought else 0
        amount = round(sum(BASES[category] * rng.uniform(.7, 1.3) for _ in range(items)), 2) if bought else 0.0
        basket = [category]
        if bought and items > 1:
            basket += list(rng.choice([p for p in PRODUCTS if p != category], size=min(items-1, len(PRODUCTS)-1), replace=False))
        rows.append({"session_id":f"S{i+1:05d}","customer_id":customer,"timestamp":(pd.Timestamp("2025-01-01")+pd.Timedelta(minutes=int(rng.integers(0,365*24*60)))).isoformat(),"device_type":str(rng.choice(["Mobile","Desktop","Tablet"],p=[.58,.34,.08])),"product_category":category,"product_basket":json.dumps(basket) if bought else "[]","actions":json.dumps(actions),"items_viewed":views,"items_added_to_cart":added,"checkout_started":checkout,"purchase_completed":bought,"session_duration_seconds":int(rng.integers(30,1800)),"total_purchase_amount":amount})
    return pd.DataFrame(rows)

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True); generate_sessions().to_csv(OUT, index=False)
