# Model Card — Holiday-Aware Completed-Trip Forecast

| Item | Value |
|---|---|
| Project | Ride-Hailing Completed-Trip Forecasting & Demand-Based Positioning |
| Training notebook | `notebooks/05_demand_forecasting.ipynb` |
| Downstream notebook | `notebooks/06_demand-based_fleet_positioning.ipynb` |
| Selected model | Holiday-Aware Historical Baseline |
| Forecast grain | Pickup zone × hour |
| Forecast horizon | 1–7 January 2025 |
| Status | Portfolio analytical model; not production-validated |

## Model Purpose

The model predicts the number of recorded completed trips for each actionable NYC pickup zone and hour. Its output supports short-horizon activity planning and relative zone-positioning analysis.

The model does not estimate all passenger requests, actual driver supply, exact vehicle requirements, or optimal dispatch decisions.

## Intended Use

Appropriate uses include:

- estimating short-horizon completed-trip activity;
- comparing expected activity across zones within the same hour;
- identifying recurring zone, hour, weekday, and holiday patterns;
- providing an input to relative completed-trip workload shares; and
- demonstrating chronological forecast evaluation.

Inappropriate uses include:

- treating completed trips as total latent demand;
- assigning an exact number of drivers or vehicles;
- automated real-time dispatching or pricing;
- evaluating individual driver performance; and
- making high-impact operational decisions without human review.

## Training Data

The source is the 2024 NYC TLC HVFHS trip dataset after the quality rules in notebooks 02–03.

| Item | Value |
|---|---:|
| Clean `fact_trip` rows | 239,426,737 |
| Completed trips within actionable forecast scope | 239,417,292 |
| Actionable pickup zones | 262 |
| Historical hours | 8,784 |
| Complete zone-hour rows | 2,301,408 |
| Zero-demand zone-hours | 91,481 |
| Missing target values | 0 |

The forecast scope excludes LocationID 264, LocationID 265, and EWR. A complete cross join of 8,784 hours and 262 zones ensures that zero-trip zone-hours remain represented.

## Target

```text
completed_trips = recorded completed pickups in one zone-hour
```

This target measures observed fulfilled activity. It excludes demand that never became a completed trip, including cancelled, rejected, unmatched, and abandoned requests.

## Temporal Evaluation Design

| Split | Period | Rows | Purpose |
|---|---|---:|---|
| Train | 1 January–31 October 2024 | 1,917,840 | Build baseline and ML candidates |
| Validation | 1–30 November 2024 | 188,640 | Compare candidates and select the model |
| Test | 1–31 December 2024 | 194,928 | Final evaluation after selection |

The split is chronological. For the final test, the selected baseline lookup is rebuilt from train plus validation data. For the January forecast, it is rebuilt from the full 2024 panel.

## Holiday Logic

The notebook uses `USFederalHolidayCalendar` and identifies 11 federal holidays in 2024:

- 8 in train;
- 2 in validation; and
- 1 in test.

Regular dates use the average completed trips for:

```text
LocationID × hour_of_day × day_of_week
```

Federal holidays use a pooled average for:

```text
LocationID × hour_of_day
```

Pooling is used because one year of data provides only one example of most named holidays. If a holiday zone-hour value is unavailable, the regular lookup is used as fallback. Predictions are clipped at zero.

## Candidate Models

### Holiday-Aware Historical Baseline

An interpretable aggregation model using the regular and pooled-holiday lookups described above.

### Linear Regression

A linear benchmark trained on historical target aggregates and calendar features. The notebook reports 15,627 negative validation predictions before clipping them to zero.

### HistGradientBoosting

The nonlinear benchmark uses:

| Parameter | Value |
|---|---:|
| Estimator | `HistGradientBoostingRegressor` |
| Loss | Poisson |
| Maximum iterations | 150 |
| Learning rate | 0.08 |
| Maximum leaf nodes | 31 |
| L2 regularization | 1.0 |
| Random state | 42 |

Poisson loss supports the non-negative count target, while histogram-based boosting is suitable for the large training table.

## Machine-Learning Features

The Linear Regression and HistGradientBoosting candidates use ten features:

| Feature | Description |
|---|---|
| `zone_avg_trips` | Historical mean for the pickup zone |
| `zone_hour_avg_trips` | Historical mean for zone and hour |
| `zone_day_avg_trips` | Historical mean for zone and day of week |
| `baseline_prediction` | Holiday-aware or regular lookup prediction |
| `hour_of_day` | Hour from 0 to 23 |
| `day_of_week` | ISO day number from 1 to 7 |
| `month` | Calendar month |
| `is_weekend` | Weekend indicator |
| `is_holiday` | Federal-holiday indicator |
| `days_since_start` | Simple time-trend feature |

Trip distance and duration are not used as demand-forecasting features because future-trip values would not be known at forecast time.

## Metrics

| Metric | Interpretation |
|---|---|
| WAPE | Total absolute error divided by total actual completed trips; primary selection metric |
| MAE | Average absolute error per zone-hour |
| MAPE nonzero | Percentage error calculated only where actual completed trips are greater than zero |
| Bias | Net overprediction or underprediction relative to actual volume |

Positive bias indicates overall overprediction. Negative bias indicates overall underprediction.

## Validation Results

| Model | WAPE | MAE | MAPE nonzero | Bias |
|---|---:|---:|---:|---:|
| **Holiday-Aware Historical Baseline** | **15.29%** | **16.19** | **24.14%** | **-1.71%** |
| HistGradientBoosting | 16.61% | 17.59 | 27.76% | 4.15% |
| Linear Regression | 18.37% | 19.46 | 28.42% | -4.43% |

The Holiday-Aware Historical Baseline is selected because it has the lowest validation WAPE. The more complex candidates do not improve performance on the held-out validation month.

## Final Test Results

| Model | WAPE | MAE | MAPE nonzero | Bias |
|---|---:|---:|---:|---:|
| Holiday-Aware Historical Baseline | **19.61%** | **21.19** | **27.55%** | **-4.99%** |

### Test performance by volume tier

| Volume tier | WAPE | MAE | Bias |
|---|---:|---:|---:|
| Low | 22.98% | 5.62 | -8.52% |
| Medium | 17.73% | 15.65 | -7.66% |
| High | 20.00% | 42.49 | -3.47% |

Low-volume zones have the highest relative error despite their lower absolute MAE. High-volume zones have higher absolute error because each zone-hour contains more completed trips.

December performance is weaker than November performance. The saved daily error table shows especially large errors around the year-end period, including 24–31 December. This indicates that one year of recurring patterns does not fully capture unusual year-end behavior.

## Forecast Output

The selected model generates 44,016 predictions for 1–7 January 2025:

```text
168 hours × 262 zones = 44,016 rows
```

The saved notebook output reports:

| Check | Result |
|---|---:|
| Unique forecast hours | 168 |
| Unique zones | 262 |
| Missing predictions | 0 |
| Negative predictions | 0 |
| Duplicate zone-hour rows | 0 |
| New Year's Day rows | 6,288 |
| Models in `forecast_output` | 1 |

New Year's Day is recognized in notebook 05 and uses the pooled holiday forecast pattern.

## Downstream Positioning Use

Notebook 06 multiplies forecasted completed trips by historical average duration to estimate completed-trip workload hours. Duration uses this fallback order:

1. zone-hour-day;
2. zone-hour;
3. zone; and
4. global average.

Each zone's workload is divided by total workload within the same hour to obtain `recommended_positioning_share_pct`. The shares sum to 100% across all 262 zones for every saved hour.

The downstream review flag combines forecast-volume-tier performance, duration fallback, and holiday status. `is_holiday`, `holiday_name`, and `calendar_reliability` are retained in the final positioning output. Holiday rows are marked `Use with caution`, unless a global duration fallback requires manual review.

## Verification Scope

Notebook 05 displays checks for panel size, preserved trip totals, split coverage, missing features, missing/negative predictions, holiday rows, duplicate keys, and saved-table counts. The saved outputs show the expected values.

These are notebook-level diagnostic checks, not a formal automated testing framework. The variable `forecast_validation_passed` is calculated but not printed or enforced, and the final saved-table query is displayed without a final `assert`, `raise`, or literal `PASSED` message.

The latest saved notebook has no error outputs, but a fresh-kernel run from top to bottom is recommended before making a stronger reproducibility claim.

## Limitations

1. **Completed trips are not total demand.** Unfulfilled and cancelled requests are not represented.
2. **Only one year of history is available.** Year-over-year seasonality and named-holiday effects cannot be estimated.
3. **Holiday observations are pooled.** Different federal holidays can have materially different patterns.
4. **External drivers are absent.** Weather, events, pricing, promotions, traffic, airport schedules, and transit disruption are not modeled.
5. **Supply data is absent.** Active drivers, available driver-hours, vehicles per zone, repositioning time/cost, and fleet constraints are unavailable.
6. **Historical aggregation adapts slowly.** Sudden structural changes or unusual events can invalidate recurring patterns.
7. **Low-volume zones are relatively uncertain.** Small absolute errors can produce large percentage errors.
8. **Predictions are not calibrated uncertainty intervals.** The pipeline provides point predictions and empirical error metrics, not probabilistic prediction intervals.
9. **Holiday reliability remains limited.** The review flag identifies holidays, but it cannot compensate for having only pooled one-year holiday history.
10. **No automated production monitoring exists.** Model drift and forecast degradation are not tracked after the notebook run.

## Responsible Use

Positioning priorities should not be the sole basis for reducing service in lower-volume communities. Human reviewers should consider geographic service coverage, fairness, safety, live events, and current supply conditions.

Do not interpret the model as evidence of individual driver productivity or as proof that a zone has sufficient or insufficient supply.

## Reproducibility

The selected model is stored as reproducible historical lookup tables and forecast outputs rather than as a serialized estimator artifact. Reproduction requires:

- the verified 2024 source files;
- notebooks 01–05 executed in order;
- the DuckDB warehouse;
- the package versions in `requirements.txt`; and
- a clean-kernel rerun for final release verification.

The main saved tables are `forecast_output`, `forecast_model_evaluation`, and `forecast_test_tier_evaluation`.

## Monitoring Recommendations

If this prototype is extended, monitor:

- WAPE, MAE, and bias by week;
- holiday versus non-holiday error;
- error by borough and volume tier;
- the share of zero-demand zone-hours;
- changes in zone-level activity distributions;
- missing zones or forecast keys; and
- the proportion of downstream rows using fallback duration estimates.
