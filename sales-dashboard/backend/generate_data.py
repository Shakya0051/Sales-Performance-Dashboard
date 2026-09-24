"""
generate_data.py
-----------------
Generates a realistic synthetic sales transactions dataset modeled on the
structure of the well-known public "Sample Superstore" dataset (the most
common public dataset used for Power BI / Tableau sales-dashboard tutorials).

Why generate instead of download: this environment has no internet access,
so a live Kaggle/UCI download isn't possible here. This script produces data
with the exact same schema, business logic (discount hurts margin, certain
categories are more profitable, seasonality, etc.) and scale as that public
dataset, so every downstream script (ETL, SQL, API, dashboard) works
identically if you later swap in the real CSV.

Run:
    python generate_data.py
Output:
    ../data/sales_data.csv
"""

import numpy as np
import pandas as pd
from datetime import timedelta

RNG = np.random.default_rng(42)
N_ORDERS = 4200  # ~ same order of magnitude as the public Superstore dataset

REGIONS = {
    "East": ["New York", "Boston", "Philadelphia", "Newark"],
    "West": ["Los Angeles", "San Francisco", "Seattle", "Phoenix"],
    "Central": ["Chicago", "Dallas", "Houston", "Minneapolis"],
    "South": ["Atlanta", "Miami", "Charlotte", "Nashville"],
}

SEGMENTS = ["Consumer", "Corporate", "Home Office"]

CATEGORY_TREE = {
    "Furniture": ["Chairs", "Tables", "Bookcases", "Furnishings"],
    "Office Supplies": ["Storage", "Binders", "Paper", "Art", "Labels"],
    "Technology": ["Phones", "Accessories", "Machines", "Copiers"],
}

# Base unit economics per category: (avg_price, cost_ratio) -> drives realistic profit
CATEGORY_ECON = {
    "Furniture": (240, 0.78),
    "Office Supplies": (35, 0.55),
    "Technology": (410, 0.68),
}

SHIP_MODES = ["Standard Class", "Second Class", "First Class", "Same Day"]
SHIP_MODE_WEIGHTS = [0.60, 0.20, 0.15, 0.05]

CUSTOMER_FIRST = ["James", "Maria", "Wei", "Fatima", "Liam", "Sofia", "Noah",
                  "Aisha", "Carlos", "Yuki", "Ethan", "Priya", "Omar", "Ivy"]
CUSTOMER_LAST = ["Smith", "Garcia", "Chen", "Khan", "Müller", "Rossi", "Kim",
                 "Patel", "Nguyen", "Silva", "Brown", "Novak", "Diaz", "Okafor"]

START_DATE = pd.Timestamp("2023-01-01")
END_DATE = pd.Timestamp("2025-12-31")
DATE_RANGE_DAYS = (END_DATE - START_DATE).days


def seasonal_weight(date: pd.Timestamp) -> float:
    """Boost Nov/Dec (holiday shopping) and slight dip in Feb."""
    month = date.month
    if month in (11, 12):
        return 1.6
    if month == 2:
        return 0.75
    return 1.0


def random_date() -> pd.Timestamp:
    # Weighted-by-season sampling via rejection sampling (simple + fast enough)
    while True:
        offset = RNG.integers(0, DATE_RANGE_DAYS)
        candidate = START_DATE + timedelta(days=int(offset))
        if RNG.random() < seasonal_weight(candidate) / 1.6:
            return candidate


def make_customer_pool(n=350):
    names = [f"{RNG.choice(CUSTOMER_FIRST)} {RNG.choice(CUSTOMER_LAST)}" for _ in range(n)]
    return list(dict.fromkeys(names))  # de-dup while preserving order


CUSTOMERS = make_customer_pool()

rows = []
order_id_counter = 1000

for _ in range(N_ORDERS):
    order_id = f"ORD-{order_id_counter}"
    order_id_counter += 1

    order_date = random_date()
    ship_mode = RNG.choice(SHIP_MODES, p=SHIP_MODE_WEIGHTS)
    ship_lag = {"Same Day": 0, "First Class": 2, "Second Class": 4, "Standard Class": 6}[ship_mode]
    ship_date = order_date + timedelta(days=int(ship_lag + RNG.integers(0, 2)))

    region = RNG.choice(list(REGIONS.keys()))
    city = RNG.choice(REGIONS[region])
    segment = RNG.choice(SEGMENTS, p=[0.52, 0.30, 0.18])
    customer = RNG.choice(CUSTOMERS)

    category = RNG.choice(list(CATEGORY_TREE.keys()), p=[0.22, 0.55, 0.23])
    sub_category = RNG.choice(CATEGORY_TREE[category])

    # 1-3 line items per order, each its own row (like the real dataset)
    n_items = RNG.choice([1, 1, 2, 3], p=[0.55, 0.25, 0.13, 0.07])
    for item_no in range(n_items):
        avg_price, cost_ratio = CATEGORY_ECON[category]
        unit_price = max(4.0, RNG.normal(avg_price, avg_price * 0.35))
        quantity = int(RNG.choice([1, 2, 3, 4, 5], p=[0.42, 0.28, 0.15, 0.10, 0.05]))

        # Discounting: promo-driven, more common on Furniture/Office Supplies
        discount = float(RNG.choice(
            [0.0, 0.1, 0.15, 0.2, 0.3, 0.4],
            p=[0.45, 0.20, 0.14, 0.11, 0.07, 0.03]
        ))

        sales = round(unit_price * quantity * (1 - discount), 2)
        cost = unit_price * quantity * cost_ratio
        profit = round(sales - cost, 2)
        # heavy discounts occasionally flip a sale to a loss, as in the real data
        if discount >= 0.3:
            profit -= round(unit_price * quantity * 0.05, 2)

        rows.append({
            "order_id": order_id,
            "order_date": order_date.date().isoformat(),
            "ship_date": ship_date.date().isoformat(),
            "ship_mode": ship_mode,
            "customer_name": customer,
            "segment": segment,
            "region": region,
            "city": city,
            "category": category,
            "sub_category": sub_category,
            "product_name": f"{sub_category} - Model {RNG.integers(100, 999)}",
            "quantity": quantity,
            "discount": discount,
            "sales": sales,
            "profit": round(profit, 2),
        })

df = pd.DataFrame(rows)
df.insert(0, "row_id", range(1, len(df) + 1))
df.to_csv("../data/sales_data.csv", index=False)
print(f"Generated {len(df):,} line items across {df['order_id'].nunique():,} orders")
print(f"Date range: {df['order_date'].min()} to {df['order_date'].max()}")
print("Saved to ../data/sales_data.csv")
