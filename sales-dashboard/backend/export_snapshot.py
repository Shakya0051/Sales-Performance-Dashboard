"""
export_snapshot.py
-------------------
Pulls every KPI query result out of sales.db and writes one JSON file.
Used to embed a real data snapshot into the static frontend artifact
(a published HTML page can't call a local Flask server), and is also
handy as a plain data export for Power BI's "Get Data > JSON".

Run:
    python export_snapshot.py
Output:
    ../data/dashboard_snapshot.json
"""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "../data/sales.db"
OUT_PATH = Path(__file__).parent / "../data/dashboard_snapshot.json"


def query(conn, sql):
    cur = conn.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def main():
    conn = sqlite3.connect(DB_PATH)
    snapshot = {
        "summary": query(conn, """
            SELECT ROUND(SUM(sales),2) AS total_revenue, ROUND(SUM(profit),2) AS total_profit,
                   ROUND(SUM(profit)*100.0/SUM(sales),2) AS profit_margin_pct,
                   COUNT(DISTINCT order_id) AS total_orders,
                   ROUND(SUM(sales)*1.0/COUNT(DISTINCT order_id),2) AS avg_order_value,
                   COUNT(DISTINCT customer_name) AS unique_customers
            FROM fact_sales;
        """)[0],
        "monthly_trend": query(conn, """
            SELECT order_ym, ROUND(SUM(sales),2) AS revenue, ROUND(SUM(profit),2) AS profit
            FROM fact_sales GROUP BY order_ym ORDER BY order_ym;
        """),
        "by_region": query(conn, """
            SELECT region, ROUND(SUM(sales),2) AS revenue, ROUND(SUM(profit),2) AS profit,
                   ROUND(SUM(profit)*100.0/SUM(sales),2) AS margin_pct
            FROM fact_sales GROUP BY region ORDER BY revenue DESC;
        """),
        "by_category": query(conn, """
            SELECT category, sub_category, ROUND(SUM(sales),2) AS revenue,
                   ROUND(SUM(profit),2) AS profit, SUM(quantity) AS units_sold
            FROM fact_sales GROUP BY category, sub_category ORDER BY revenue DESC;
        """),
        "top_customers": query(conn, """
            SELECT customer_name, segment, ROUND(SUM(sales),2) AS revenue,
                   ROUND(SUM(profit),2) AS profit, COUNT(DISTINCT order_id) AS orders
            FROM fact_sales GROUP BY customer_name, segment ORDER BY revenue DESC LIMIT 10;
        """),
        "segment_mix": query(conn, """
            SELECT segment, ROUND(SUM(sales),2) AS revenue,
                   ROUND(SUM(sales)*100.0/(SELECT SUM(sales) FROM fact_sales),1) AS pct_of_revenue
            FROM fact_sales GROUP BY segment ORDER BY revenue DESC;
        """),
        "discount_impact": query(conn, """
            SELECT
                CASE WHEN discount = 0 THEN 'No discount'
                     WHEN discount <= 0.15 THEN 'Low (<=15%)'
                     WHEN discount <= 0.30 THEN 'Medium (16-30%)'
                     ELSE 'High (>30%)' END AS discount_band,
                ROUND(AVG(profit_margin)*100,2) AS avg_margin_pct,
                ROUND(SUM(sales),2) AS revenue
            FROM fact_sales GROUP BY discount_band ORDER BY revenue DESC;
        """),
    }
    conn.close()
    OUT_PATH.write_text(json.dumps(snapshot, indent=2))
    print(f"Wrote snapshot to {OUT_PATH}")


if __name__ == "__main__":
    main()
