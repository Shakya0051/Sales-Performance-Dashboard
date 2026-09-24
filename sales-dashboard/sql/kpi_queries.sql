-- kpi_queries.sql
-- Core business-performance queries against fact_sales (SQLite).
-- Each one backs an endpoint in backend/app.py and can also be pasted
-- straight into Power BI's "Get Data > ODBC/SQLite > Advanced query".

-- 1. Headline KPIs (single row: total revenue, profit, margin, orders, AOV)
SELECT
    ROUND(SUM(sales), 2)                              AS total_revenue,
    ROUND(SUM(profit), 2)                              AS total_profit,
    ROUND(SUM(profit) * 100.0 / SUM(sales), 2)         AS profit_margin_pct,
    COUNT(DISTINCT order_id)                           AS total_orders,
    ROUND(SUM(sales) * 1.0 / COUNT(DISTINCT order_id), 2) AS avg_order_value,
    COUNT(DISTINCT customer_name)                       AS unique_customers
FROM fact_sales;

-- 2. Monthly revenue & profit trend
SELECT
    order_ym,
    ROUND(SUM(sales), 2)  AS revenue,
    ROUND(SUM(profit), 2) AS profit
FROM fact_sales
GROUP BY order_ym
ORDER BY order_ym;

-- 3. Revenue & profit by region
SELECT
    region,
    ROUND(SUM(sales), 2)  AS revenue,
    ROUND(SUM(profit), 2) AS profit,
    ROUND(SUM(profit) * 100.0 / SUM(sales), 2) AS margin_pct
FROM fact_sales
GROUP BY region
ORDER BY revenue DESC;

-- 4. Revenue & profit by category / sub-category
SELECT
    category,
    sub_category,
    ROUND(SUM(sales), 2)  AS revenue,
    ROUND(SUM(profit), 2) AS profit,
    SUM(quantity)          AS units_sold
FROM fact_sales
GROUP BY category, sub_category
ORDER BY revenue DESC;

-- 5. Top 10 customers by revenue
SELECT
    customer_name,
    segment,
    ROUND(SUM(sales), 2) AS revenue,
    ROUND(SUM(profit), 2) AS profit,
    COUNT(DISTINCT order_id) AS orders
FROM fact_sales
GROUP BY customer_name, segment
ORDER BY revenue DESC
LIMIT 10;

-- 6. Customer segment mix
SELECT
    segment,
    ROUND(SUM(sales), 2) AS revenue,
    ROUND(SUM(sales) * 100.0 / (SELECT SUM(sales) FROM fact_sales), 1) AS pct_of_revenue
FROM fact_sales
GROUP BY segment
ORDER BY revenue DESC;

-- 7. Discount impact on margin (buckets)
SELECT
    CASE
        WHEN discount = 0 THEN 'No discount'
        WHEN discount <= 0.15 THEN 'Low (<=15%)'
        WHEN discount <= 0.30 THEN 'Medium (16-30%)'
        ELSE 'High (>30%)'
    END AS discount_band,
    ROUND(AVG(profit_margin) * 100, 2) AS avg_margin_pct,
    ROUND(SUM(sales), 2) AS revenue,
    COUNT(*) AS line_items
FROM fact_sales
GROUP BY discount_band
ORDER BY revenue DESC;

-- 8. Orders shipped late risk proxy: fulfillment days by ship mode
SELECT
    ship_mode,
    ROUND(AVG(fulfillment_days), 2) AS avg_fulfillment_days,
    COUNT(*) AS orders
FROM fact_sales
GROUP BY ship_mode
ORDER BY avg_fulfillment_days;

-- 9. Loss-making line items (for a "problem orders" table/drill-through)
SELECT
    order_id, order_date, customer_name, category, sub_category,
    sales, discount, profit
FROM fact_sales
WHERE profit < 0
ORDER BY profit ASC
LIMIT 25;
