"""
etl.py
------
Extract-Transform-Load pipeline:
  1. Extract: read the raw sales CSV with Pandas.
  2. Transform: clean types, validate ranges, engineer date parts,
     handle any duplicates/nulls.
  3. Load: write into a normalized-ish SQLite database (sales.db) that
     Power BI, the Flask API, or any BI tool can connect to directly.

Run:
    python etl.py
Output:
    ../data/sales.db   (SQLite database)
"""

import sqlite3
import pandas as pd

RAW_CSV = "../data/sales_data.csv"
DB_PATH = "../data/sales.db"


def extract(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["order_date", "ship_date"])
    print(f"Extracted {len(df):,} rows")
    return df


def transform(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)

    # Drop exact duplicates
    df = df.drop_duplicates()

    # Basic validation: sales must be > 0, quantity >= 1
    df = df[(df["sales"] > 0) & (df["quantity"] >= 1)]

    # Fill any stray nulls defensively
    df["discount"] = df["discount"].fillna(0.0)
    df["profit"] = df["profit"].fillna(0.0)

    # Engineer date parts used constantly in BI reporting
    df["order_year"] = df["order_date"].dt.year
    df["order_month"] = df["order_date"].dt.month
    df["order_month_name"] = df["order_date"].dt.strftime("%b")
    df["order_ym"] = df["order_date"].dt.strftime("%Y-%m")
    df["order_quarter"] = df["order_date"].dt.quarter.map(lambda q: f"Q{q}")
    df["fulfillment_days"] = (df["ship_date"] - df["order_date"]).dt.days

    # Derived KPIs kept at row-level for convenience in SQL
    df["profit_margin"] = (df["profit"] / df["sales"]).round(4)
    df["is_loss"] = df["profit"] < 0

    after = len(df)
    print(f"Transform complete: {before:,} -> {after:,} rows "
          f"({before - after} dropped as invalid/duplicate)")
    return df


def load(df: pd.DataFrame, db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        df.to_sql("fact_sales", conn, if_exists="replace", index=False)

        # Lightweight star-schema-style dimension views for cleaner BI modeling
        conn.execute("""
            CREATE VIEW IF NOT EXISTS dim_product AS
            SELECT DISTINCT category, sub_category, product_name
            FROM fact_sales;
        """)
        conn.execute("""
            CREATE VIEW IF NOT EXISTS dim_customer AS
            SELECT DISTINCT customer_name, segment, region, city
            FROM fact_sales;
        """)
        conn.execute("""
            CREATE VIEW IF NOT EXISTS dim_date AS
            SELECT DISTINCT order_date, order_year, order_month,
                   order_month_name, order_ym, order_quarter
            FROM fact_sales;
        """)

        # Helpful indexes for the API / dashboard queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_order_date ON fact_sales(order_date);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_region ON fact_sales(region);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON fact_sales(category);")
        conn.commit()
        print(f"Loaded into {db_path} -> table 'fact_sales' "
              f"+ views dim_product / dim_customer / dim_date")
    finally:
        conn.close()


if __name__ == "__main__":
    raw = extract(RAW_CSV)
    clean = transform(raw)
    load(clean, DB_PATH)
