"""Shopping analytics and customer segmentation."""
import ast
import json
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

REQUIRED_COLUMNS = ["session_id", "customer_id", "timestamp", "device_type", "product_category", "actions", "items_viewed", "items_added_to_cart", "checkout_started", "purchase_completed", "session_duration_seconds", "total_purchase_amount"]

def parse_actions(value):
    if isinstance(value, (list, tuple)): return list(value)
    if pd.isna(value): return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (ValueError, TypeError):
        try:
            parsed = ast.literal_eval(str(value))
            return parsed if isinstance(parsed, list) else []
        except (ValueError, SyntaxError): return []

def validate_data(frame):
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing: raise ValueError("Missing required columns: " + ", ".join(missing))
    result = frame.copy()
    for col in ("items_viewed", "items_added_to_cart", "session_duration_seconds", "total_purchase_amount"):
        result[col] = pd.to_numeric(result[col], errors="coerce").fillna(0).clip(lower=0)
    for col in ("checkout_started", "purchase_completed"):
        result[col] = result[col].fillna(False).astype(str).str.lower().isin(["true", "1", "yes"])
    result["actions"] = result["actions"].apply(parse_actions)
    result["timestamp"] = pd.to_datetime(result["timestamp"], errors="coerce")
    result["device_type"] = result["device_type"].fillna("Unknown")
    result["product_category"] = result["product_category"].fillna("Unknown")
    result["customer_id"] = result["customer_id"].fillna("Unknown")
    return result

def calculate_metrics(data):
    df = validate_data(data)
    n = len(df); purchased = df.purchase_completed; added = df.items_added_to_cart.gt(0); checkout = df.checkout_started
    safe_pct = lambda numerator, denominator: float(numerator.sum() / denominator.sum() * 100) if denominator.sum() else 0.0
    return {"total_sessions": n, "unique_customers": int(df.customer_id.nunique()), "purchases": int(purchased.sum()),
            "conversion_rate": safe_pct(purchased, pd.Series(True, index=df.index)),
            "cart_abandonment_rate": safe_pct(added & ~purchased, added),
            "checkout_abandonment_rate": safe_pct(checkout & ~purchased, checkout),
            "average_session_duration": float(df.session_duration_seconds.mean()) if n else 0.0,
            "average_order_value": float(df.loc[purchased, "total_purchase_amount"].mean()) if purchased.any() else 0.0,
            "revenue_by_category": df.loc[purchased].groupby("product_category").total_purchase_amount.sum().sort_values(ascending=False),
            "conversion_by_device": df.groupby("device_type").purchase_completed.mean().mul(100).sort_values(ascending=False),
            "popular_actions": pd.Series([a for actions in df.actions for a in actions]).value_counts(),
            "common_sequences": df.actions.apply(lambda x: " → ".join(x) or "No actions").value_counts().head(10)}

def segment_customers(data, n_clusters=4, random_state=42):
    df = validate_data(data)
    if df.empty: return None, None, "No sessions are available for segmentation."
    features = df.assign(_added=df.items_added_to_cart.gt(0).astype(int), _purchase=df.purchase_completed.astype(int))
    customers = features.groupby("customer_id").agg(number_of_sessions=("session_id", "count"), total_purchases=("_purchase", "sum"), average_session_duration=("session_duration_seconds", "mean"), average_order_value=("total_purchase_amount", lambda x: x[features.loc[x.index, "purchase_completed"]].mean() if features.loc[x.index, "purchase_completed"].any() else 0), cart_abandonment_frequency=("_added", lambda x: int((x.astype(bool) & ~features.loc[x.index, "purchase_completed"]).sum())), purchase_conversion_frequency=("_purchase", "mean"))
    if len(customers) < 2: return customers, None, "At least two customers are needed to form clusters."
    k = max(2, min(int(n_clusters), len(customers)))
    x = StandardScaler().fit_transform(customers.fillna(0))
    customers["cluster"] = KMeans(n_clusters=k, random_state=random_state, n_init=10).fit_predict(x)
    summary = customers.groupby("cluster").mean(numeric_only=True)
    return customers, summary, None
