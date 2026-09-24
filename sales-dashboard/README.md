# Sales Performance Dashboard

A full pipeline from raw transactions to a live dashboard, built the way a
real analytics stack is: **Pandas** for data prep, **SQL/SQLite** as the
warehouse layer, a small **Flask API** as the backend, an **HTML/JS**
frontend for a fast web view, and a **Power BI** connection for the
BI-tool layer.


```
sales-dashboard/
├── backend/
│   ├── generate_data.py     # builds a Superstore-style sample dataset (no internet needed)
│   ├── etl.py                # Pandas clean → SQLite load (fact_sales table + views)
│   ├── export_snapshot.py    # dumps all KPI queries to one JSON file
│   ├── app.py                 # Flask REST API serving the KPI queries as JSON
│   └── requirements.txt
├── sql/
│   └── kpi_queries.sql       # every KPI query, documented, reusable in Power BI
├── data/
│   ├── sales_data.csv        # raw generated transactions
│   ├── sales.db               # SQLite warehouse (fact_sales + dim views)
│   └── dashboard_snapshot.json
└── frontend/
    └── index.html             # standalone dashboard (works offline, embeds a data snapshot)
```

## Why a generated dataset

This environment has no internet access, so I couldn't pull the actual
public Kaggle "Sample Superstore" file. `generate_data.py` instead
synthesizes data with the **same schema, scale, and business logic**
(seasonality, discount-driven margin loss, category economics) as that
dataset. Swap in a real CSV with the same column names at any time —
nothing downstream needs to change.

## 1. Run the pipeline

```bash
cd backend
pip install -r requirements.txt

python generate_data.py     # -> ../data/sales_data.csv
python etl.py                # -> ../data/sales.db
python export_snapshot.py    # -> ../data/dashboard_snapshot.json
```

## 2. Run the backend API

```bash
python app.py
# -> http://localhost:5000/api/summary
# -> http://localhost:5000/api/monthly-trend
# -> http://localhost:5000/api/by-region
# -> http://localhost:5000/api/by-category
# -> http://localhost:5000/api/top-customers
# -> http://localhost:5000/api/segment-mix
# -> http://localhost:5000/api/discount-impact
```

## 3. Frontend

`frontend/index.html` is self-contained — open it directly in a browser,
no server required. It ships with a snapshot of real data baked in. To
make it live against your running API instead of the snapshot, replace
the `const DATA = {...}` block with:

```js
const [summary, monthly, region, category, customers, segment, discount] =
  await Promise.all([
    fetch('http://localhost:5000/api/summary').then(r=>r.json()),
    fetch('http://localhost:5000/api/monthly-trend').then(r=>r.json()),
    fetch('http://localhost:5000/api/by-region').then(r=>r.json()),
    fetch('http://localhost:5000/api/by-category').then(r=>r.json()),
    fetch('http://localhost:5000/api/top-customers').then(r=>r.json()),
    fetch('http://localhost:5000/api/segment-mix').then(r=>r.json()),
    fetch('http://localhost:5000/api/discount-impact').then(r=>r.json()),
  ]);
const DATA = { summary, monthly_trend: monthly, by_region: region,
               by_category: category, top_customers: customers,
               segment_mix: segment, discount_impact: discount };
```

(Re-run `export_snapshot.py` any time to refresh the baked-in copy instead.)

## 4. Connect Power BI

Power BI Desktop can read the SQLite warehouse three different ways —
pick whichever fits:

**Option A — SQLite directly (recommended)**
1. Install the community "SQLite" connector (or the free `Sqlite ODBC
   Driver`) if Power BI doesn't list SQLite under Get Data by default.
2. Get Data → More → Database → SQLite → point it at `data/sales.db`.
3. Load table `fact_sales` (and the `dim_product` / `dim_customer` /
   `dim_date` views if you want a lighter star-schema model).
4. Build measures with DAX equivalents of `sql/kpi_queries.sql`, e.g.:
   ```
   Total Revenue = SUM(fact_sales[sales])
   Total Profit  = SUM(fact_sales[profit])
   Profit Margin % = DIVIDE([Total Profit], [Total Revenue])
   ```

**Option B — CSV**
Get Data → Text/CSV → `data/sales_data.csv`. Simplest option; you lose
the pre-built views/indexes but Power BI's own Power Query can replicate
the transforms in `etl.py`.

**Option C — Live via the Flask API**
Get Data → Web → `http://localhost:5000/api/monthly-trend` (repeat per
endpoint). Good if you want Power BI to reflect the live app rather than
a static export — just make sure `app.py` is running when you refresh.

## Notes

- I can't generate an actual `.pbix` file for you (Power BI's format
  isn't something that can be authored outside Power BI Desktop), but
  everything the data model, KPIs, and queries need is in `sql/` and
  `data/` — building the report itself is just wiring up visuals to
  Option A/B/C above.
- The published web dashboard is the fast way to see the same KPIs
  without installing anything.
