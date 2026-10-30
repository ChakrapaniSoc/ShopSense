"""Frequent product baskets and association rules using mlxtend."""
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules

def mine_patterns(data, min_support=0.08, min_confidence=0.3):
    required = {"purchase_completed", "product_category"}
    if not required.issubset(data.columns): raise ValueError("Required columns: purchase_completed, product_category")
    purchased = data[data.purchase_completed.astype(str).str.lower().isin(["true", "1", "yes"])]
    if len(purchased) < 2: return pd.DataFrame(), "At least two completed transactions are required."
    source = purchased["product_basket"] if "product_basket" in purchased.columns else purchased.product_category
    baskets = source.fillna("").astype(str).apply(lambda value: __import__("json").loads(value) if value.startswith("[") else value.split("|"))
    baskets = baskets.apply(lambda xs: list(dict.fromkeys(str(x).strip() for x in xs if str(x).strip())))
    universe = sorted({item for basket in baskets for item in basket})
    if len(universe) < 2: return pd.DataFrame(), "Need at least two distinct products/categories across transactions."
    matrix = pd.DataFrame([{item: item in basket for item in universe} for basket in baskets], dtype=bool)
    itemsets = apriori(matrix, min_support=float(min_support), use_colnames=True)
    if itemsets.empty or itemsets.itemsets.map(len).max() < 2: return pd.DataFrame(), "No frequent combinations meet the selected support threshold."
    rules = association_rules(itemsets, metric="confidence", min_threshold=float(min_confidence))
    if rules.empty: return pd.DataFrame(), "No association rules meet the selected confidence threshold."
    rules["antecedents"] = rules.antecedents.map(lambda x: ", ".join(sorted(x)))
    rules["consequents"] = rules.consequents.map(lambda x: ", ".join(sorted(x)))
    return rules.sort_values(["lift", "confidence", "support"], ascending=False), None
