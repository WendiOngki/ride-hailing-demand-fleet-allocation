# Ride-Hailing Demand Forecasting & Demand-Based Positioning

**Spatiotemporal completed-trip forecasting and relative positioning analytics using NYC TLC High-Volume For-Hire Services data**

> From historical trip records to transparent, demand-based positioning guidance.

## Business Problem

Ride-hailing operations teams need to understand when and where completed-trip activity occurs, forecast short-horizon activity, and translate that forecast into interpretable zone-level positioning priorities.

This project builds an end-to-end analytical pipeline using official New York City Taxi and Limousine Commission (NYC TLC) High-Volume For-Hire Services (HVFHS) trip records. The final recommendations are expressed as relative positioning shares, not absolute driver or vehicle counts, because the dataset does not contain fleet-supply information.

## Data

- **Source:** NYC TLC HVFHS monthly Parquet releases and the official Taxi Zone Lookup table.
- **Period:** January–December 2024.
- **Files:** 12 monthly trip files plus 1 zone lookup file.
- **Raw records:** 239,470,448 trips.
- **Clean `fact_trip` records:** 239,426,737 trips.
- **Raw schema:** 24 columns, consistent across all 12 monthly files.
- **Forecasting scope:** 262 actionable pickup zones, excluding LocationID 264, LocationID 265, and EWR.
- **Forecast grain:** one row per pickup zone per hour.

Checksums, file sizes, source URLs, and acquisition status are recorded in the data manifest.

## Pipeline

The project is organized into six sequential notebooks:

| Notebook | Purpose |
|---|---|
| `01_data_acquisition.ipynb` | Verify or download 12 monthly HVFHS files and the zone lookup, then record checksums and acquisition metadata. |
| `02_initial_data_quality_audit.ipynb` | Audit schema consistency, timestamps, zones, distance, duration, missing values, and potential duplicates. |
| `03_data_warehouse_construction.ipynb` | Build the DuckDB analytical warehouse: `dim_zone`, `dim_base`, `dim_time`, and `fact_trip`. |
| `04_descriptive_and_proxy_analytics.ipynb` | Analyze temporal and spatial patterns, trip distance and duration, zone stability, and completed-trip activity proxies. |
| `05_demand_forecasting.ipynb` | Build the complete zone-hour panel, compare forecasting candidates, add holiday-aware forecasting, evaluate the selected model, and save future forecasts. |
| `06_demand-based_fleet_positioning.ipynb` | Convert forecasts into completed-trip workload proxies, relative positioning shares, priority tiers, and reliability flags. |

## Data Quality Decisions

The complete 239,470,448-row raw dataset was audited before warehouse construction.

| Check | Rows affected | Share of raw data | Decision |
|---|---:|---:|---|
| Schema inconsistency | 0 | 0% | No action |
| Invalid timestamp order | 9,680 | 0.004042% | Remove |
| Invalid pickup/drop-off zone | 0 | 0% | No action |
| Non-positive trip distance | 34,059 | 0.014223% | Remove |
| Non-positive trip duration | 30 | 0.000013% | Remove |
| Missing critical values | 0 | 0% | No action |
| Potential duplicate rows | 440 extra rows across 439 groups | Very small | Retain because they are not exact duplicates |
| Exact duplicate rows | 0 | 0% | No action |

Because a record can fail more than one rule, the invalid categories cannot be added directly. The combined filtering removes 43,711 rows (0.018253%) and retains 239,426,737 rows (99.981747%).

Only non-positive distance and duration values are removed. No upper distance or duration cap is applied, so unusual but positive trips remain available for analysis.

## Analytical Warehouse

The processed data is stored in `data/processed/nyc_taxi.db` using DuckDB.

| Table | Description |
|---|---|
| `dim_zone` | NYC taxi zone reference. |
| `dim_base` | HVFHS platform and dispatch-base reference. |
| `dim_time` | Complete 2024 hourly calendar with 8,784 timestamps. |
| `fact_trip` | Clean trip-level fact table with 239,426,737 records. |
| `forecast_output` | Seven-day zone-hour completed-trip forecast. |
| `forecast_model_evaluation` | Validation and test model metrics. |
| `forecast_test_tier_evaluation` | Test performance by zone volume tier. |
| `fleet_allocation_recommendation` | Legacy table name containing relative demand-based positioning recommendations. |

Despite the legacy table name, `fleet_allocation_recommendation` does not represent actual fleet capacity or absolute driver allocation.

## Descriptive and Proxy Analytics

The descriptive analysis covers:

- hourly, daily, weekday, and weekend demand patterns;
- pickup boroughs, pickup zones, and borough-to-borough flows;
- distance and duration distributions;
- complete daily-zone panels including zero-trip days;
- average daily completed trips and demand stability by zone;
- completed-trip hours as an occupied-trip workload proxy.

Completed-trip hours measure historical passenger-trip activity. They are not available driver-hours and are not a supply-capacity measure.

## Forecasting Approach

### Complete forecasting panel

The forecasting mart contains 2,301,408 rows:

```text
8,784 hourly timestamps × 262 actionable zones = 2,301,408 zone-hours
```

Zero-trip zone-hours are explicitly retained so the model learns from a complete time-zone panel.

### Time-based split

The data is split chronologically to prevent future information from entering earlier evaluation periods:

| Split | Period | Rows |
|---|---|---:|
| Train | 1 January–31 October 2024 | 1,917,840 |
| Validation | 1–30 November 2024 | 188,640 |
| Test | 1–31 December 2024 | 194,928 |

### Holiday feature

The pipeline identifies 11 US federal holiday dates in 2024 using `USFederalHolidayCalendar`.

The historical baseline uses two patterns:

- regular dates: average demand by zone, hour, and day of week;
- federal holidays: pooled historical holiday demand by zone and hour.

The holiday pattern is pooled because one year of data provides only one example of each named annual holiday. Treating each holiday name as a separate high-confidence pattern would overfit a single date.

### Candidate models

Three forecasting candidates are evaluated:

1. Holiday-Aware Historical Baseline;
2. Linear Regression;
3. HistGradientBoosting with Poisson loss.

### Validation performance

| Model | WAPE | MAE | MAPE, nonzero | Bias |
|---|---:|---:|---:|---:|
| Holiday-Aware Historical Baseline | **15.29%** | **16.19** | **24.14%** | **-1.71%** |
| HistGradientBoosting | 16.61% | 17.59 | 27.76% | 4.15% |
| Linear Regression | 18.37% | 19.46 | 28.42% | -4.43% |

The Holiday-Aware Historical Baseline is selected because it has the lowest validation WAPE and MAE.

### Final test performance

| Model | WAPE | MAE | MAPE, nonzero | Bias |
|---|---:|---:|---:|---:|
| Holiday-Aware Historical Baseline | **19.61%** | **21.19** | **27.55%** | **-4.99%** |

Test performance by historical zone-volume tier:

| Volume tier | WAPE | MAE | Bias |
|---|---:|---:|---:|
| Low | 22.98% | 5.62 | -8.52% |
| Medium | 17.73% | 15.65 | -7.66% |
| High | 20.00% | 42.49 | -3.47% |

The lower MAE of low-volume zones should not be interpreted as higher relative accuracy. Their WAPE remains the highest because a small absolute error can be large relative to sparse demand.

## Future Forecast

The final forecast covers 1–7 January 2025:

```text
7 days × 24 hours × 262 zones = 44,016 forecast rows
```

The 6,288 rows for 1 January are marked as New Year's Day and use the holiday-aware demand pattern.

## Demand-Based Positioning Logic

Notebook 06 translates forecasted completed trips into relative positioning guidance through the following steps:

1. Estimate historical average trip duration using a fallback hierarchy: zone-hour-day, zone-hour, zone, then global average.
2. Calculate forecasted completed-trip hours:

   ```text
   forecasted trips × historical average trip minutes ÷ 60
   ```

3. Calculate each zone's share of total forecasted completed-trip hours within the same hour.
4. Rank zones within each forecast hour.
5. Assign positioning priorities using cumulative workload share:
   - **High:** zones contributing to the first 50%;
   - **Medium:** zones contributing from 50% to 80%;
   - **Standard:** remaining zones.
6. Add forecast, duration, calendar, and manual-review reliability flags.

The hourly positioning shares are validated to sum to 100% across all 262 zones.

## Outputs

The pipeline produces:

- `forecast_output` in DuckDB;
- `forecast_model_evaluation` in DuckDB;
- `forecast_test_tier_evaluation` in DuckDB;
- `fleet_allocation_recommendation` in DuckDB;
- `outputs/fleet_allocation_recommendation.parquet`;
- an all-zone positioning-priority visualization.

## Key Limitations

- **Completed trips are not total latent demand.** Cancelled, rejected, unmatched, or abandoned requests are not fully represented.
- **No active-driver data.** The data does not contain active drivers by hour or zone.
- **No available driver-hours.** Completed-trip hours are an occupied-trip workload proxy, not available supply.
- **No vehicles per zone.** Positioning shares cannot be converted directly into absolute vehicle counts.
- **No repositioning time or cost.** Travel time between zones is not optimized.
- **No supply constraints.** The recommendations do not enforce fleet size, shift schedules, driver availability, or vehicle capacity.
- **Limited holiday history.** Only one calendar year is available, so holiday forecasts use a pooled holiday pattern.
- **No weather, event, pricing, or promotion features.** Forecasts cannot explain or anticipate shocks from variables that are not present.
- **No causal claims.** The analysis identifies patterns and builds forecasts; it does not establish why demand changed.
- **Relative and advisory output.** Positioning recommendations support human review and are not automated dispatch instructions.

## Reproduction

1. Create and activate the project environment.
2. Install packages from `requirements.txt`.
3. Run the notebooks in order:

   ```text
   01 → 02 → 03 → 04 → 05 → 06
   ```

4. Shut down earlier notebook kernels before a later notebook writes to `nyc_taxi.db`, preventing DuckDB connection conflicts.
5. Confirm that the final validation cell in each notebook returns `PASSED`.

Large raw and processed data files are intentionally excluded from Git. They are reproduced through the acquisition and warehouse notebooks.

## Technology Stack

- Python
- DuckDB SQL
- pandas
- NumPy
- scikit-learn
- Matplotlib
- Seaborn
- Plotly
- Parquet
- Jupyter Notebook

## Project Status

The six-notebook analytical pipeline is complete and validated. Dashboard and supporting documentation are included and are being finalized against the latest holiday-aware forecast and demand-based positioning outputs.
