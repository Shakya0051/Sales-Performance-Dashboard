"""
app.py
------
Flask REST API backend for the Sales Performance Dashboard.

Serves JSON for every KPI in sql/kpi_queries.sql. This is what the frontend
(frontend/index.html) calls, and it's also a valid data source for Power BI
via Get Data > Web (point it at http://localhost:5000/api/monthly-trend etc.)

Run:
    pip install flask flask-cors
    python app.py
Then open:
    http://localhost:5000/api/summary
"""

import sqlite3
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS

DB_PATH = Path(__file__).parent / "../data/sales.db"

app = Flask(__name__)
CORS(app)  # allow the static frontend (served from a different port/file) to call this API


def query(sql: str, params: tuple = ()) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


@app.get("/api/summary")
def summary():
    rows = query("""
        SELECT
            ROUND(SUM(sales), 2) AS total_revenue,
            ROUND(SUM(profit), 2) AS total_profit,
            ROUND(SUM(profit) * 100.0 / SUM(sales), 2) AS profit_margin_pct,
            COUNT(DISTINCT order_id) AS total_orders,
            ROUND(SUM(sales) * 1.0 / COUNT(DISTINCT order_id), 2) AS avg_order_value,
            COUNT(DISTINCT customer_name) AS unique_customers
        FROM fact_sales;
    """)
    return jsonify(rows[0])


@app.get("/api/monthly-trend")
def monthly_trend():
    rows = query("""
        SELECT order_ym, ROUND(SUM(sales),2) AS revenue, ROUND(SUM(profit),2) AS profit
        FROM fact_sales GROUP BY order_ym ORDER BY order_ym;
    """)
    return jsonify(rows)


@app.get("/api/by-region")
def by_region():
    rows = query("""
        SELECT region, ROUND(SUM(sales),2) AS revenue, ROUND(SUM(profit),2) AS profit,
               ROUND(SUM(profit)*100.0/SUM(sales),2) AS margin_pct
        FROM fact_sales GROUP BY region ORDER BY revenue DESC;
    """)
    return jsonify(rows)


@app.get("/api/by-category")
def by_category():
    rows = query("""
        SELECT category, sub_category, ROUND(SUM(sales),2) AS revenue,
               ROUND(SUM(profit),2) AS profit, SUM(quantity) AS units_sold
        FROM fact_sales GROUP BY category, sub_category ORDER BY revenue DESC;
    """)
    return jsonify(rows)


@app.get("/api/top-customers")
def top_customers():
    rows = query("""
        SELECT customer_name, segment, ROUND(SUM(sales),2) AS revenue,
               ROUND(SUM(profit),2) AS profit, COUNT(DISTINCT order_id) AS orders
        FROM fact_sales GROUP BY customer_name, segment
        ORDER BY revenue DESC LIMIT 10;
    """)
    return jsonify(rows)


@app.get("/api/segment-mix")
def segment_mix():
    rows = query("""
        SELECT segment, ROUND(SUM(sales),2) AS revenue,
               ROUND(SUM(sales)*100.0/(SELECT SUM(sales) FROM fact_sales),1) AS pct_of_revenue
        FROM fact_sales GROUP BY segment ORDER BY revenue DESC;
    """)
    return jsonify(rows)


@app.get("/api/discount-impact")
def discount_impact():
    rows = query("""
        SELECT
            CASE
                WHEN discount = 0 THEN 'No discount'
                WHEN discount <= 0.15 THEN 'Low (<=15%)'
                WHEN discount <= 0.30 THEN 'Medium (16-30%)'
                ELSE 'High (>30%)'
            END AS discount_band,
            ROUND(AVG(profit_margin)*100, 2) AS avg_margin_pct,
            ROUND(SUM(sales), 2) AS revenue
        FROM fact_sales GROUP BY discount_band ORDER BY revenue DESC;
    """)
    return jsonify(rows)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
