# NYC Ride-Hailing Demand Forecasting & Demand-Based Fleet Positioning

An end-to-end analytics case study using 2024 NYC TLC High Volume For-Hire Services (HVFHS) trip records to examine completed-trip patterns, forecast short-horizon activity, and produce relative pickup-zone positioning guidance.

> The forecasting analysis estimates recorded completed-trip activity. It does not measure total latent passenger demand or actual fleet capacity.

## Business Problem

Ride-hailing operations need to understand where and when trip activity concentrates and how expected workload varies across pickup zones. This analysis answers three questions:

1. What temporal and geographic patterns appear in completed trips?
2. Which forecasting approach performs best for zone-hour completed-trip volume?
3. How can the forecast be translated into transparent relative positioning priorities?

Because the public data does not contain active-driver counts, available driver-hours, vehicles per zone, repositioning time, or supply constraints, the final output is directional positioning guidance rather than an exact fleet-allocation plan.

## Data

| Item                      |                                                    Value |
| ------------------------- | -------------------------------------------------------: |
| Source                    | NYC TLC HVFHS monthly Parquet files and Taxi Zone Lookup |
| Historical period         |                                    January–December 2024 |
| Source files              |                    12 monthly trip files + 1 zone lookup |
| Raw trip rows             |                                              239,470,448 |
| Clean `fact_trip` rows    |                                              239,426,737 |
| Actionable forecast zones |                                                      262 |
| Hourly timestamps in 2024 |                                                    8,784 |
| Complete zone-hour rows   |                                                2,301,408 |

The forecasting scope excludes LocationID 264, LocationID 265, and EWR. After this geographic restriction, the hourly panel preserves **239,417,292** completed trips. The difference from the complete `fact_trip` total comes from records outside the actionable positioning scope.

## Analytical Workflow

| Notebook                                   | Purpose                                                                                                                                                      | Main evidence saved in the notebook                            |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------- |
| `01_data_acquisition.ipynb`                | Download or reuse the 13 source files, calculate SHA-256 checksums, and save the acquisition manifest.                                                       | 13 expected, existing, non-empty, and valid-checksum files.    |
| `02_initial_data_quality_audit.ipynb`      | Audit file coverage, schema, timestamps, zones, distance, duration, missing values, and duplicates.                                                          | Cleaning summary and `data_quality_audit_2024.csv`.            |
| `03_data_warehouse_construction.ipynb`     | Build the DuckDB dimensions and clean trip fact table.                                                                                                       | Quality, relationship, and table-row summaries.                |
| `04_descriptive_and_proxy_analytics.ipynb` | Analyze temporal, spatial, distance, duration, stability, and completed-trip workload patterns.                                                              | Tables, charts, and five final boolean checks equal to `True`. |
| `05_demand_forecasting.ipynb`              | Build the complete hourly panel, compare three forecasting candidates, test the selected model, and generate a seven-day forecast.                           | Model metrics, forecast tables, and structural checks.         |
| `06_demand-based_fleet_positioning.ipynb`  | Convert predicted completed trips into completed-trip workload shares, ranks, priorities, and reliability flags, then export the compact dashboard database. | 44,016 positioning rows and eight validated dashboard tables.  |

Run the notebooks in numerical order because every stage depends on outputs from earlier stages.

## Data Quality Decisions

| Check                      | Rows affected | Decision                                     |
| -------------------------- | ------------: | -------------------------------------------- |
| Schema inconsistency       |             0 | No action                                    |
| Invalid timestamp order    |         9,680 | Remove                                       |
| Invalid zone reference     |             0 | No action                                    |
| Non-positive trip distance |        34,059 | Remove                                       |
| Non-positive trip duration |            30 | Remove                                       |
| Missing critical values    |             0 | No action                                    |
| Potential duplicate rows   |           440 | Retain because they are not exact duplicates |
| Exact duplicate rows       |             0 | No action                                    |

A row can fail more than one rule. Therefore, the individual invalid counts should not be added directly. The combined rules remove **43,711 rows (0.018253%)** and retain **239,426,737 rows (99.981747%)**.

Only non-positive distances and durations are removed. Positive extreme trips are retained rather than automatically classified as invalid.

## DuckDB Analytical Warehouse

The full development warehouse is stored locally at `data/processed/nyc_taxi.db`. It supports the analytical notebooks but is excluded from GitHub because it contains the large trip-level fact table.

| Table                             | Rows in the saved notebook output | Description                                             |
| --------------------------------- | --------------------------------: | ------------------------------------------------------- |
| `dim_zone`                        |                               265 | Taxi zone reference                                     |
| `dim_base`                        |                                 2 | Uber and Lyft license/base combinations                 |
| `dim_time`                        |                             8,784 | Complete 2024 hourly time dimension                     |
| `fact_trip`                       |                       239,426,737 | Clean trip-level records                                |
| `forecast_output`                 |                            44,016 | Zone-hour forecast for 1–7 January 2025                 |
| `forecast_model_evaluation`       |                                 4 | Three validation results and one final test result      |
| `forecast_test_tier_evaluation`   |                                 3 | Test metrics for Low, Medium, and High volume tiers     |
| `fleet_allocation_recommendation` |                            44,016 | Relative positioning recommendations; legacy table name |

Despite its legacy name, `fleet_allocation_recommendation` does not contain absolute vehicle requirements.

### Compact Dashboard Database

The repository includes a separate aggregate-only database for the Streamlit dashboard:

```text
data/dashboard/ride_hailing_dashboard.duckdb
```

The database is approximately **4.26 MB** and excludes the 239,426,737-row trip-level `fact_trip` table. It contains only the validated summaries and outputs required by the dashboard.

| Dashboard table                 |   Rows |
| ------------------------------- | -----: |
| `historical_summary`            |      1 |
| `daily_trend`                   |    366 |
| `weekday_weekend`               |      2 |
| `hourly_heatmap`                |    168 |
| `forecast_model_evaluation`     |      4 |
| `forecast_test_tier_evaluation` |      3 |
| `forecast_output`               | 44,016 |
| `positioning_recommendation`    | 44,016 |

`positioning_recommendation` is the deployment-facing table name exported from the legacy development table `fleet_allocation_recommendation`. Both represent relative demand-based positioning guidance, not vehicle allocation.

## Main Descriptive Findings

- Average daily completed trips are **630,214 on weekdays** and **714,525 on weekends**.
- The average peak hour is **18:00** with approximately **38,609 trips per day**; the lowest is **03:00** with approximately **9,740**.
- Manhattan accounts for **38.87%** of recorded pickups, followed by Brooklyn at 26.38%, Queens at 20.92%, and the Bronx at 12.35%.
- LaGuardia Airport and JFK Airport are the two busiest pickup zones by completed-trip count.
- The overall average trip is **5.08 miles** and **20.13 minutes**; the medians are 3.01 miles and 16.32 minutes.
- The completed daily-zone panel contains **95,892 rows**, including **1,596 zero-trip zone-days**.
- Among the busiest zones, East Village and Bushwick South have higher daily coefficients of variation than East Chelsea and Times Square.

Completed-trip hours represent occupied passenger-trip workload. They are not available driver-hours or a supply-capacity measure.

## Forecasting Design

### Target and panel

The target is the number of completed trips for one pickup zone in one hour. Zero-demand zone-hours are explicitly included.

```text
8,784 hours × 262 zones = 2,301,408 zone-hour rows
```

### Chronological split

| Split      | Period                    |      Rows |
| ---------- | ------------------------- | --------: |
| Train      | 1 January–31 October 2024 | 1,917,840 |
| Validation | 1–30 November 2024        |   188,640 |
| Test       | 1–31 December 2024        |   194,928 |

The model is selected on validation data. Test data is used only after selection.

### Candidate models

1. Holiday-Aware Historical Baseline;
2. Linear Regression; and
3. HistGradientBoosting with Poisson loss.

The historical baseline uses:

- a regular pattern by zone, hour, and day of week; and
- a pooled federal-holiday pattern by zone and hour.

The notebook identifies 11 US federal holidays in 2024: eight in train, two in validation, and one in test.

### Validation results

| Model                                 |       WAPE |       MAE | MAPE nonzero |       Bias |
| ------------------------------------- | ---------: | --------: | -----------: | ---------: |
| **Holiday-Aware Historical Baseline** | **15.29%** | **16.19** |   **24.14%** | **-1.71%** |
| HistGradientBoosting                  |     16.61% |     17.59 |       27.76% |      4.15% |
| Linear Regression                     |     18.37% |     19.46 |       28.42% |     -4.43% |

The Holiday-Aware Historical Baseline is selected because it has the lowest validation WAPE.

### Final test results

| Model                             |       WAPE |       MAE | MAPE nonzero |       Bias |
| --------------------------------- | ---------: | --------: | -----------: | ---------: |
| Holiday-Aware Historical Baseline | **19.61%** | **21.19** |   **27.55%** | **-4.99%** |

Test WAPE by historical zone-volume tier is 22.98% for Low, 17.73% for Medium, and 20.00% for High. The overall negative bias indicates underprediction across the December test period.

## January 2025 Forecast Scenario

The final lookup was rebuilt using the complete 2024 dataset and used to generate an out-of-time forecast scenario for 1–7 January 2025. This is a historical portfolio demonstration rather than a current or real-time forecast.

```text
7 days × 24 hours × 262 zones = 44,016 forecast rows
```

All saved forecast rows have a prediction and volume tier. There are no negative or duplicate zone-hour predictions. The 6,288 rows on 1 January are recognized as New Year's Day and use the pooled holiday pattern.

## Positioning Logic

Notebook 06 applies the following steps:

1. Estimate historical trip duration using this fallback order: zone-hour-day, zone-hour, zone, then global average.
2. Calculate forecasted completed-trip hours:

   ```text
   forecast completed trips × historical average trip minutes ÷ 60
   ```

3. Divide each zone's predicted completed-trip hours by the total for the same forecast hour.
4. Rank all 262 zones within each hour.
5. Assign priorities using cumulative workload share:
   - **High:** zones entering before the cumulative share reaches 50%;
   - **Medium:** zones entering between 50% and 80%;
   - **Standard:** the remaining zones.
6. Attach forecast, duration, and calendar reliability information.

Every saved forecast hour contains 262 zones, ranks 1–262, and positioning shares summing to 100%.

The final review flags contain:

| Review flag               |   Rows |  Share |
| ------------------------- | -----: | -----: |
| Standard use              | 25,056 | 56.92% |
| Use with caution          | 18,624 | 42.31% |
| Manual review recommended |    336 |  0.76% |

The review flag is based on forecast-volume-tier reliability, duration fallback, and holiday status. Holiday rows are marked `Use with caution`, unless a global duration fallback produces the higher-priority `Manual review recommended` flag.

## Verification Actually Implemented

The notebooks use practical checks such as:

- expected versus actual row counts;
- missing, negative, and duplicate counts;
- preservation of aggregated trip totals;
- dimension/fact relationship checks;
- forecast-date, zone, and holiday-row coverage;
- hourly positioning shares summing to 100%; and
- saved-table row and key checks.

The saved notebook outputs show these checks returning the expected values. Notebook 06 also validates the eight compact dashboard tables against their expected row counts and reports that all dashboard database checks passed. These are in-notebook validation checks rather than a separate formal automated test suite.

For a stronger reproducibility claim, restart the kernel and run every notebook from top to bottom before release.

## Repository Structure

```text
ride-hailing-demand-fleet-allocation/
├── dashboard/
│   └── app.py
├── data/
│   ├── dashboard/
│   │   └── ride_hailing_dashboard.duckdb
│   ├── manifests/
│   ├── raw/                              # ignored by Git
│   └── processed/                        # ignored by Git
├── docs/
│   ├── EXECUTIVE_MEMO.md
│   └── MODEL_CARD.md
├── notebooks/
│   ├── 01_data_acquisition.ipynb
│   ├── 02_initial_data_quality_audit.ipynb
│   ├── 03_data_warehouse_construction.ipynb
│   ├── 04_descriptive_and_proxy_analytics.ipynb
│   ├── 05_demand_forecasting.ipynb
│   └── 06_demand-based_fleet_positioning.ipynb
├── outputs/                 # ignored by Git
├── .gitignore
├── README.md
└── requirements.txt
```

## How to Reproduce

### Run the dashboard

The compact dashboard database is included in the repository, so the dashboard can run without downloading the raw trip files or rebuilding the full analytical warehouse.

```bash
python -m pip install -r requirements.txt
python -m streamlit run dashboard/app.py
```

### Reproduce the full analysis

Full analytical reproduction requires the source NYC TLC files. From the repository root, start Jupyter Lab:

```bash
jupyter lab
```

Run notebooks 01–06 in numerical order. Close DuckDB-writing notebook connections before another process writes to `data/processed/nyc_taxi.db`.

## Technology

Python, DuckDB SQL, pandas, NumPy, scikit-learn, Matplotlib, Seaborn, Plotly, Streamlit, Parquet, and Jupyter Notebook.

## Limitations

- Completed trips do not include all cancelled, rejected, unmatched, or abandoned requests.
- Only one year of history is available.
- Federal holidays are pooled rather than modeled separately by holiday name.
- Weather, events, airport schedules, traffic, pricing, promotions, and transit disruption are not included.
- Active drivers, available driver-hours, vehicles per zone, repositioning time/cost, and fleet constraints are unavailable.
- The output is not causal, real time, or a dispatch optimization system.
- Low-volume zones have higher relative forecasting uncertainty.
- Exact staffing or vehicle counts cannot be inferred from positioning shares.

## Documentation

- [Model Card](docs/MODEL_CARD.md)
- [Executive Memo](docs/EXECUTIVE_MEMO.md)

## Status

The analytical pipeline, forecast tables, relative positioning output, dashboard, and documentation are complete for portfolio presentation. The compact dashboard database has passed all eight table-level row-count checks. The latest saved notebook outputs contain no execution-error cells, but a clean-kernel end-to-end rerun remains recommended before describing the full workflow as fully reproducible or production-ready.
