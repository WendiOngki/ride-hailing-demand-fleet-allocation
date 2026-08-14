# Ride-Hailing Demand & Fleet Allocation Analytics

**Spatiotemporal Demand Forecasting and Driver Allocation Analytics Using NYC TLC High-Volume For-Hire Vehicle Trip Data**

> From trip records to smarter driver allocation.

---

## Business Problem

Ride-hailing operations teams need a reproducible way to understand demand patterns across zones and time, forecast short-horizon demand, and translate forecasts into fleet-allocation guidance — while preserving the context and limitations of trip-completion data that does not capture unmatched demand (requests that were cancelled, rejected, or never fulfilled).

This project builds that pipeline end-to-end using NYC TLC's official High-Volume For-Hire Services (HVFHS) trip records — a full year (January–December 2024) of real, regulator-mandated Uber/Lyft trip data.

## Data

- **Source:** NYC Taxi & Limousine Commission (TLC) — High-Volume For-Hire Services Trip Records, official monthly Parquet releases, plus the official Taxi Zone Lookup table.
- **Period:** January–December 2024, 12 monthly files, locked as a snapshot with checksums recorded.
- **Raw volume:** 239,470,448 trip records across 12 files, 24 columns, schema verified identical across all months.
- **Grain:** one row = one trip (raw); aggregated to zone × hour × date for forecasting.

## Methodology

The pipeline follows six stages, each in its own notebook:

| Notebook | Purpose |
|---|---|
| `01_data_acquisition.ipynb` | Download 12 months of HVFHS data + zone lookup, compute and persist checksums |
| `02_initial_data_quality_audit.ipynb` | Six audits on raw data: schema consistency, referential/timestamp validity, distribution/outliers/completeness, duplicate detection, scope decision |
| `03_data_warehouse.ipynb` | Build `dim_zone`, `dim_base`, `dim_time`, `fact_trip` in DuckDB with documented filters, deduplication, and SQL tests |
| `04_descriptive_and_proxy_analytics.ipynb` | Temporal/spatial demand patterns, zone volatility, supply-demand proxy |
| `05_demand_forecasting.ipynb` | Aggregated zone-hour-date mart, baseline vs. Gradient Boosting model, rolling-origin backtest, evaluation by volume tier |
| `06_fleet_allocation_logic.ipynb` | Uncertainty intervals, relative allocation ratios, final recommendation output |

### Data Quality & Scope Decisions

Audited on the full 239,470,448-row raw dataset before any filtering:

| Criterion | Rows Affected | % of Total | Decision |
|---|---|---|---|
| Schema consistency (12 months) | 0 (all identical) | — | No action needed |
| dropoff_datetime ≤ pickup_datetime | 9,680 | ~0.004% | Removed |
| PULocationID/DOLocationID invalid | 0 | 0% | No action needed |
| trip_miles ≤ 0 | 34,059 | ~0.014% | Removed |
| trip_time ≤ 0 | 30 | ~0.00001% | Removed |
| hvfhs_license_num / dispatching_base_num missing | 0 | 0% | No action needed |
| Duplicate trip rows | 879 (439 combinations) | ~0.00037% | Deduplicated (kept 1 per combination) |

**Final `fact_trip`:** 239,426,298 rows. Total impact of all filtering + deduplication: ~0.018% of raw data — not material to any aggregate reported in this project.

Extreme values (e.g., a single 555-mile trip, or a 15.3-hour trip) were intentionally **not** removed via simple statistical thresholds (e.g., cutting at the 99th percentile), because legitimate long-distance trips (airport runs, out-of-city trips) can reasonably fall far above typical percentiles. No blunt distance/duration cap was applied at the warehouse stage.

### Forecasting Approach

- **Mart:** 2,215,471 rows at zone × hour × date grain, built from the cleaned `fact_trip`.
- **Split:** rolling-origin (time-based), not random — train on Jan 1–Nov 6, test on Nov 7–Dec 31, to avoid temporal leakage.
- **Baseline:** historical average per (zone, hour, day-of-week) combination — WAPE 18.22%, MAPE 27.95%.
- **Advanced model:** Gradient Boosting Regressor, iteratively improved through feature engineering (zone/hour/day-of-week target encoding, trip distance/duration stats, time-of-day segmentation) — final WAPE 17.43%, MAPE 26.48%.

**Performance by zone volume tier** (zones split into Low/Medium/High by historical average volume):

| Tier | Baseline WAPE | Model WAPE | Baseline MAPE | Model MAPE |
|---|---|---|---|---|
| Low | 22.61% | 22.63% | 41.62% | 39.90% |
| Medium | 17.38% | 17.10% | 19.33% | 19.42% |
| High | 18.07% | 16.97% | 24.32% | 21.52% |

The model's advantage over baseline is concentrated in high-volume zones; for low-volume zones, results are mixed — a limitation rooted in the inherent unpredictability of sparse count data, not a fixable modeling gap.

### Fleet Allocation Logic

- **Uncertainty intervals:** built from each zone's WAPE tier, with a 1-trip minimum margin so near-zero predictions still convey uncertainty rather than false precision.
- **Allocation recommendation:** expressed as a **ratio** relative to each zone-hour's historical average capacity (`zone_hour_avg`), not an absolute driver count — the dataset contains no data on actual driver counts per zone.
- **Categories:** Increase Allocation (≥120% of historical average), Reduce Allocation (≤80%), Maintain Allocation (otherwise). These thresholds are a design choice, not an industry standard.

## Key Limitations

- **Completed trips ≠ total demand.** This dataset only records trips that were completed; it does not capture requests that were cancelled, rejected, or never matched to a driver.
- **No driver-count data.** All "utilization" and "allocation" metrics are proxies built from trip-time and trip-volume alone — not true driver utilization or true fleet sizing.
- **No causal claims.** No conclusions are drawn about pricing, promotions, or weather effects on demand; none of that data is present in this dataset.
- **No cross-platform benchmarking.** Uber vs. Lyft is never framed as "which is better" — this dataset is not designed for competitive benchmarking.
- **No individual driver or vehicle identification.**
- **Forecast performance varies by zone volume**, as shown above — recommendations for low-volume zones carry wider uncertainty and should be treated with more caution than high-volume zones.
- **Allocation recommendations are relative and advisory**, not an automated dispatch decision — human review is required before operational use.

## How to Reproduce

1. Set up the `project-ride-hailing` conda environment (see `environment.yml` / package list).
2. Run notebooks in order: `01` → `02` → `03` → `04` → `05` → `06`.
3. Each notebook is self-contained (re-establishes its own DuckDB connection and paths) but depends on tables built by earlier notebooks in `../data/processed/nyc_taxi.db`.
4. `05` and `06` persist their outputs (`forecast_output`, `fleet_allocation_recommendation`) as tables in the same DuckDB file, so `06` does not require re-running the model training in `05`.
5. Raw data snapshot (12 monthly Parquet files + zone lookup) and checksums are recorded in `01_data_acquisition.ipynb`.

## Stack

Python, DuckDB SQL, pandas, scikit-learn (GradientBoostingRegressor), matplotlib/seaborn.

## Status

Core pipeline (Fase 1–7) complete. Dashboard, model card, and executive memo in progress.
