# CommerceIQ — Power BI Build Guide

Power BI Desktop isn't installed in the build environment, and `.pbix` is a
closed binary format with no CLI/API — so this guide (plus the star schema
CSVs in `star_schema_export/`) is the deliverable in place of a pre-built
`.pbix`. Follow it in Power BI Desktop to assemble the same 4 pages as the
Streamlit dashboard (`dashboard/`), which **is** the tested, working
version of this project.

Regenerate the CSVs any time with `python src/export_powerbi_star_schema.py`
(run after `load_to_db.py`, `rfm.py`, and `churn.py`).

---

## 1. Import the data

1. Power BI Desktop → **Get Data → Folder** → point at `powerbi/star_schema_export/`.
2. **Combine & Transform** → select all 7 CSVs.
3. In Power Query, set data types explicitly (Power BI's auto-detect is usually
   right, but double check): all `*_date`/`date` columns → Date, `revenue`/
   `cost`/`profit`/`spend`/`amount`-type columns → Decimal Number.

## 2. Build the star schema (Model view)

```
DimCustomer ───┐
DimProduct  ───┼──< FactSales >───── DimDate
DimChannel  ───┘         (order_date)

DimChannel ───< FactSessions >──── DimDate   (session_date)
DimChannel ───< FactMarketing >─── DimDate   (start_date)
```

Relationships to create (all single-direction, 1-to-many, dimension → fact):

| From | To | On |
|---|---|---|
| DimCustomer[customer_id] | FactSales[customer_id] | 1:* |
| DimProduct[product_id] | FactSales[product_id] | 1:* |
| DimDate[date] | FactSales[order_date] | 1:* |
| DimChannel[channel] | FactSessions[channel] | 1:* |
| DimDate[date] | FactSessions[session_date] | 1:* |
| DimChannel[channel] | FactMarketing[channel] | 1:* |
| DimDate[date] | FactMarketing[start_date] | 1:* |

**Attribution limitation (be upfront about this on the dashboard, don't hide it):**
`FactSales` has no channel/campaign_id — orders aren't attributed to a
marketing touchpoint in this schema (matching the source PDF's own table
design). `FactSessions` and `FactMarketing` connect to `DimChannel`
independently of `FactSales`. This means channel-level ROAS/CAC measures
below are an explicit **proxy** (conversions × overall AOV), not
order-level attributed revenue — say so in a text box on the Marketing page.

## 3. DAX measures

Create a dedicated measure table (Modeling → New Table → `_Measures = ROW("x", 0)`,
hide the `x` column) and add these as new measures on it.

### Revenue & Profit
```dax
Total Revenue = SUM(FactSales[revenue])

Total Cost = SUM(FactSales[cost])

Total Profit = [Total Revenue] - [Total Cost]

Margin % = DIVIDE([Total Profit], [Total Revenue])

Total Orders = DISTINCTCOUNT(FactSales[order_id])

AOV = DIVIDE([Total Revenue], [Total Orders])

Revenue (Completed Only) =
CALCULATE([Total Revenue], FactSales[order_status] <> "Cancelled")
```

### Growth & trend
```dax
Revenue LM =
CALCULATE([Total Revenue], DATEADD(DimDate[date], -1, MONTH))

Revenue MoM % = DIVIDE([Total Revenue] - [Revenue LM], [Revenue LM])

Revenue YTD = TOTALYTD([Total Revenue], DimDate[date])

Revenue Running Total =
CALCULATE([Total Revenue], FILTER(ALLSELECTED(DimDate[date]), DimDate[date] <= MAX(DimDate[date])))
```

### Returns
```dax
Return Count = DISTINCTCOUNT('FactReturns'[return_id])   -- if you also import returns.csv as a fact
Return Rate % = DIVIDE([Return Count], [Total Orders])
```
> Note: `returns` wasn't included in the star export (kept the export to
> the 7 tables needed for the 4 planned pages). To add a Return Rate tile,
> import `data/cleaned/returns.csv` as an extra fact table joined to
> `FactSales[order_id]`, or precompute return rate in `src/export_powerbi_star_schema.py`
> and add it as a `DimProduct` column instead — either works.

### Customer
```dax
Total Customers = DISTINCTCOUNT(DimCustomer[customer_id])

Repeat Customers =
CALCULATE(
    DISTINCTCOUNTX(FactSales, FactSales[customer_id]),
    FILTER(
        VALUES(FactSales[customer_id]),
        CALCULATE(DISTINCTCOUNT(FactSales[order_id])) > 1
    )
)

Repeat Purchase Rate % = DIVIDE([Repeat Customers], [Total Customers])

Customer Lifetime Value = DIVIDE([Total Revenue], [Total Customers])
```

### RFM (reads DimCustomer[rfm_segment], already computed by src/rfm.py)
```dax
Champions Count = CALCULATE([Total Customers], DimCustomer[rfm_segment] = "Champions")

RFM Segment % of Customers =
DIVIDE([Total Customers], CALCULATE([Total Customers], ALL(DimCustomer[rfm_segment])))
```

### Marketing (proxy attribution — see §2 caveat)
```dax
Total Spend = SUM(FactMarketing[spend])

Total Conversions = SUM(FactMarketing[conversions])

CAC = DIVIDE([Total Spend], [Total Conversions])

Overall AOV (Unfiltered) = CALCULATE([AOV], ALL(FactSales))

Estimated Attributed Revenue = [Total Conversions] * [Overall AOV (Unfiltered)]

ROAS = DIVIDE([Estimated Attributed Revenue], [Total Spend])

CTR % = DIVIDE(SUM(FactMarketing[clicks]), SUM(FactMarketing[impressions]))

Campaign Conversion Rate % = DIVIDE(SUM(FactMarketing[conversions]), SUM(FactMarketing[clicks]))
```

### Funnel (from FactSessions)
```dax
Total Sessions = COUNTROWS(FactSessions)

Product Views = CALCULATE(COUNTROWS(FactSessions), FactSessions[pages_viewed] > 1)

Add to Cart Count = CALCULATE(COUNTROWS(FactSessions), FactSessions[added_to_cart] = TRUE)

Purchase Count = CALCULATE(COUNTROWS(FactSessions), FactSessions[purchased] = TRUE)

Session Conversion Rate % = DIVIDE([Purchase Count], [Total Sessions])
```

## 4. Page-by-page build guide

### Page 1 — Executive Dashboard
- Card visuals: `[Total Revenue]`, `[Total Orders]`, `[Total Customers]`,
  `[AOV]`, `[Total Profit]`, Return Rate.
- Line chart: `DimDate[date]` (month) × `[Total Revenue]`.
- Bar chart: `DimProduct[category]` × `[Total Revenue]`.
- Bar chart: Top 10 `DimProduct[product_name]` × `[Total Revenue]` (Top N filter).
- Bar/map: `DimCustomer[state]` × `[Total Revenue]`.

### Page 2 — Customer Analytics
- Cards: `[Total Customers]`, `[Repeat Purchase Rate %]`, `[Customer Lifetime Value]`.
- Donut chart: `DimCustomer[rfm_segment]` × `[Total Customers]`.
- Bar chart: `DimCustomer[risk_tier]` × `[Total Customers]`.
- Bar chart: `DimCustomer[state]` × `[Total Customers]` (top 10).
- Bar chart: `DimCustomer[membership_tier]` × `[Total Revenue]`.

### Page 3 — Product Analytics
- Scatter chart: X = units sold (`SUM(FactSales[quantity])`), Y = `[Total Profit]`,
  legend = `DimProduct[category]` — add two constant reference lines at the
  median X/Y (Analytics pane → Median line) to reproduce the quadrant view.
- Table: `DimProduct[category]`, `[Total Revenue]`, `[Total Profit]`, `[Margin %]`.
- Table: `DimProduct[product_name]`, units sold, revenue, margin — sortable.

### Page 4 — Marketing & Funnel Analytics
- Cards: `[Total Spend]`, `[CAC]`, `[ROAS]`, `[CTR %]`, `[Session Conversion Rate %]`.
- Bar chart: `DimChannel[channel]` × `[CAC]`.
- Bar chart: `DimChannel[channel]` × `[ROAS]`.
- Funnel visual: stage = {Visitors, Product Views, Add to Cart, Purchases} ×
  the corresponding measures.
- **Text box with the attribution caveat from §2**, visible on this page.

## 5. Slicers / interactive filters (every page)

Add a slicer panel synced across all 4 pages (Format → Edit interactions,
or a bookmark-based filter panel) with:

`DimDate[date]` (range), `DimCustomer[state]`, `DimProduct[category]`,
`DimProduct[product_name]`, `DimCustomer[rfm_segment]`,
`DimCustomer[membership_tier]`, `DimChannel[channel]`, `FactSessions[device]`

This mirrors the Streamlit dashboard's sidebar filters exactly
(`dashboard/data_loader.py`), so both deliverables answer the same
"show me X for Y in date range Z" questions.
