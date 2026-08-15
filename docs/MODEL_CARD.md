# Model Card — Holiday-Aware Completed-Trip Forecast

**Project:** Ride-Hailing Demand Forecasting & Demand-Based Positioning<br>
**Training notebook:** `05_demand_forecasting.ipynb`<br>
**Downstream notebook:** `06_demand-based_fleet_positioning.ipynb`<br>
**Status:** Final analytical model for this portfolio project; not production-validated

## 1. Model overview

| Item                 | Description                                                                     |
| -------------------- | ------------------------------------------------------------------------------- |
| Forecasting task     | Predict the number of completed trips for every actionable pickup zone and hour |
| Selected model       | Holiday-Aware Historical Baseline                                               |
| Model family         | Historical aggregation/look-up model                                            |
| Forecast horizon     | 1–7 January 2025                                                                |
| Forecast granularity | Pickup zone × hour                                                              |
| Candidate models     | Holiday-Aware Historical Baseline, Linear Regression, and HistGradientBoosting  |
| Selection criterion  | Lowest validation WAPE                                                          |
| Primary output       | `forecast_completed_trips`                                                      |
| Downstream use       | Relative demand-based vehicle-positioning guidance                              |

The selected model estimates expected completed-trip volume from historical patterns for the same zone, hour, and day of week. Federal holidays use a separate pooled holiday pattern. It outperformed both machine-learning candidates on the November 2024 validation period.

## 2. Intended use

The model is intended to:

- forecast short-horizon completed-trip activity by pickup zone and hour;
- identify when and where completed-trip workload is likely to concentrate;
- provide an input for relative fleet-positioning recommendations; and
- demonstrate a leakage-aware time-series validation workflow.

The model is **not** intended to:

- estimate all passenger demand, including unfulfilled or cancelled requests;
- determine the exact number of vehicles or drivers required;
- perform real-time dispatching, routing, pricing, or driver scheduling; or
- replace operational judgement during unusual events.

## 3. Data and analytical scope

### 3.1 Source data

The project uses 2024 NYC TLC High Volume For-Hire Vehicle trip records and the NYC taxi-zone lookup. After quality filtering, `fact_trip` contains **239,426,737** completed-trip records.

The forecasting panel contains:

| Item                      |     Value |
| ------------------------- | --------: |
| Actionable pickup zones   |       262 |
| Hourly timestamps in 2024 |     8,784 |
| Complete zone-hour rows   | 2,301,408 |
| Zero-completed-trip rows  |    91,481 |
| Missing target values     |         0 |

The complete panel explicitly includes zone-hours with zero completed trips. This prevents inactive periods from disappearing during aggregation and gives every time split the same spatial coverage.

### 3.2 Geographic scope

The analysis covers 262 actionable NYC taxi zones. Administrative/unknown zone IDs 264 and 265 and EWR are excluded from operational positioning because they do not represent comparable NYC pickup areas for this use case.

### 3.3 Temporal split

The data is split chronologically rather than randomly.

| Split      | Period            |      Rows | Purpose                                        |
| ---------- | ----------------- | --------: | ---------------------------------------------- |
| Train      | 1 Jan–31 Oct 2024 | 1,917,840 | Build candidate models and historical patterns |
| Validation | 1–30 Nov 2024     |   188,640 | Compare candidates and select the model        |
| Test       | 1–31 Dec 2024     |   194,928 | Final out-of-sample evaluation                 |

The validation and test periods occur strictly after their corresponding training periods. This better represents a real forecasting workflow and prevents future records from informing earlier predictions.

## 4. Prediction target

The target is:

```text
completed_trips = number of recorded completed pickups in one zone-hour
```

This is an **observed completed-trip activity measure**, not a complete measure of latent passenger demand. The dataset does not identify requests that were cancelled, rejected, unfulfilled, or never made because supply was unavailable.

## 5. Holiday-aware historical baseline

### 5.1 Regular-day pattern

For regular dates, the model calculates the average completed trips for each:

```text
LocationID × hour_of_day × day_of_week
```

This represents the recurring weekly and intraday demand pattern of each pickup zone.

### 5.2 Holiday pattern

Federal holiday dates are generated with `USFederalHolidayCalendar`. The 2024 data contains 11 federal holidays distributed as follows:

| Split      | Holiday dates |
| ---------- | ------------: |
| Train      |             8 |
| Validation |             2 |
| Test       |             1 |

Because only one year of history is available, creating a separate profile for every holiday would be too sparse. Holiday observations are therefore pooled into an average pattern for each:

```text
LocationID × hour_of_day
```

If a holiday profile is unavailable for a zone-hour, the model falls back to its regular zone-hour-day-of-week pattern. Predictions are clipped at zero.

### 5.3 Final forecast lookup

After model selection, the test prediction lookup is rebuilt with train and validation data. After final evaluation, the January 2025 forecast lookup is rebuilt with the full 2024 dataset.

The selected model is consequently represented by reproducible aggregation tables rather than a serialized estimator file.

## 6. Candidate models

### 6.1 Holiday-Aware Historical Baseline

The baseline uses the holiday or regular historical lookup described above. It is interpretable, computationally efficient, and closely matches the strong repeating zone-hour-weekday structure in the data.

### 6.2 Linear Regression

Linear Regression provides a simple parametric benchmark. It tests whether a weighted linear combination of temporal and historical-demand features improves upon the historical lookup. Negative outputs are clipped to zero.

### 6.3 HistGradientBoosting

`HistGradientBoostingRegressor` tests whether nonlinear relationships and feature interactions improve the forecast. Its main configuration is:

| Parameter          |   Value |
| ------------------ | ------: |
| Loss               | Poisson |
| Maximum iterations |     150 |
| Learning rate      |    0.08 |
| Maximum leaf nodes |      31 |
| L2 regularization  |     1.0 |
| Random state       |      42 |

Poisson loss is appropriate for a non-negative count target. HistGradientBoosting is also more memory-efficient than conventional gradient boosting for the 1.9-million-row training set.

## 7. Machine-learning features

The two machine-learning candidates use:

| Feature               | Meaning                                         |
| --------------------- | ----------------------------------------------- |
| `zone_avg_trips`      | Historical average for the pickup zone          |
| `zone_hour_avg_trips` | Historical average for the zone and hour        |
| `zone_day_avg_trips`  | Historical average for the zone and day of week |
| `baseline_prediction` | Holiday-aware or regular historical prediction  |
| `hour_of_day`         | Hour from 0 to 23                               |
| `day_of_week`         | Day number from Monday to Sunday                |
| `month`               | Calendar month                                  |
| `is_weekend`          | Weekend indicator                               |
| `is_holiday`          | Federal-holiday indicator                       |
| `days_since_start`    | Simple time-trend feature                       |

Historical features used for validation and test predictions are derived only from earlier splits. Trip distance and trip duration are not used as demand-forecasting features because they are not known for future trips at prediction time.

`LocationID` is not treated as a continuous numeric feature. Zone-specific information is represented through historical aggregate features.

## 8. Evaluation protocol

### 8.1 Model selection

All candidates are compared on November 2024 validation data. The candidate with the lowest WAPE is selected. December 2024 remains untouched until selection is complete.

### 8.2 Metrics

| Metric       | Purpose                                                                |
| ------------ | ---------------------------------------------------------------------- |
| WAPE         | Primary metric; total absolute error relative to total actual volume   |
| MAE          | Average absolute error in completed trips per zone-hour                |
| MAPE nonzero | Average percentage error only where actual demand is greater than zero |
| Bias         | Direction and size of systematic over- or underprediction              |

Positive bias means overall overprediction; negative bias means overall underprediction. MAPE excludes zero targets to avoid division by zero and unstable percentages.

## 9. Model results

### 9.1 Validation performance

| Model                                 |  WAPE (%) |       MAE | MAPE nonzero (%) |  Bias (%) |
| ------------------------------------- | --------: | --------: | ---------------: | --------: |
| **Holiday-Aware Historical Baseline** | **15.29** | **16.19** |        **24.14** | **-1.71** |
| HistGradientBoosting                  |     16.61 |     17.59 |            27.76 |      4.15 |
| Linear Regression                     |     18.37 |     19.46 |            28.42 |     -4.43 |

The historical baseline is selected because it achieves the lowest validation WAPE and MAE. The result shows that greater model complexity does not automatically improve forecast quality when the dominant patterns are strongly seasonal and repeatable.

### 9.2 Final test performance

| Model                             | WAPE (%) |   MAE | MAPE nonzero (%) | Bias (%) |
| --------------------------------- | -------: | ----: | ---------------: | -------: |
| Holiday-Aware Historical Baseline |    19.61 | 21.19 |            27.55 |    -4.99 |

Performance is weaker in December than in November, and the negative bias indicates overall underprediction. The difference is consistent with year-end behavior being harder to represent using only one year of pooled historical patterns.

### 9.3 Test performance by demand-volume tier

| Volume tier | WAPE (%) |   MAE | Bias (%) |
| ----------- | -------: | ----: | -------: |
| Low         |    22.98 |  5.62 |    -8.52 |
| Medium      |    17.73 | 15.65 |    -7.66 |
| High        |    20.00 | 42.49 |    -3.47 |

Low-volume zones have the highest relative error and underprediction bias. High-volume zones have a larger absolute error because each zone-hour contains more trips. These tier results are passed to the positioning stage as forecast-reliability information.

## 10. Forecast output

The final model produces forecasts for 1–7 January 2025.

| Check                     | Result |
| ------------------------- | -----: |
| Forecast hours            |    168 |
| Zones per hour            |    262 |
| Forecast rows             | 44,016 |
| Missing predictions       |      0 |
| Negative predictions      |      0 |
| Holiday rows on 1 January |  6,288 |

New Year's Day uses the pooled federal-holiday profile. Other dates use their regular zone-hour-day-of-week patterns.

## 11. Downstream positioning logic

Notebook 06 converts predicted completed trips into a **completed-trip workload proxy**:

```text
forecast completed-trip hours
= forecast completed trips × historical average trip duration
```

Average duration uses a transparent fallback hierarchy:

1. zone-hour-day-of-week historical duration;
2. zone-hour historical duration;
3. zone historical duration; and
4. global historical duration.

Within each forecast hour, each zone receives a relative positioning share:

```text
zone forecast completed-trip hours / total forecast completed-trip hours
```

Zones are then labelled High, Medium, or Standard priority from cumulative positioning share. Reliability flags combine forecast-volume-tier error, duration-source specificity, and holiday status.

Despite the legacy DuckDB table name `fleet_allocation_recommendation`, the output is **relative demand-based positioning guidance**, not an estimate of actual fleet capacity or an optimized allocation of a known number of vehicles.

## 12. Limitations

1. **Completed trips are not total demand.** Unfulfilled, rejected, and cancelled requests are not represented.
2. **Only one year of training history is available.** Long-term trends and year-over-year holiday effects cannot be estimated reliably.
3. **Federal holidays are pooled.** New Year's Day, Thanksgiving, and other holidays may have different spatial and hourly patterns.
4. **No external event features are included.** Weather, concerts, sports events, transit disruption, promotions, pricing, and airport schedules may affect demand.
5. **No supply information is available.** The dataset has no active-driver counts, available driver-hours, vehicles by zone, repositioning time or cost, or operational supply constraints.
6. **Historical averages adapt slowly to abrupt change.** Structural breaks or unusual events can make prior patterns unreliable.
7. **Sparse and low-volume zones have higher relative uncertainty.** Their recommendations should be treated more cautiously.
8. **The holiday calendar is federal only.** Local observances and non-federal events are not captured.
9. **The ML benchmarks rely on historical target aggregates.** Their production implementation must recreate these features strictly from data available before forecast time.

## 13. Responsible use and misuse risks

Repeatedly prioritizing only high-volume zones may reduce attention to lower-volume communities. Forecast volume should therefore not be the sole basis for service availability decisions.

The output should be used with human review, especially for:

- federal holidays and unusual events;
- low-volume zones;
- rows using broader duration fallbacks;
- periods showing distribution drift; and
- decisions that affect driver welfare or geographic service equity.

Do not interpret positioning shares as mandatory driver assignments or proof of insufficient supply.

## 14. Reproducibility

The workflow is reproducible through `05_demand_forecasting.ipynb` using the cleaned DuckDB tables constructed in notebooks 01–03. Key controls include:

- chronological train, validation, and test splits;
- complete zone-hour panels including zeros;
- explicit federal-holiday generation;
- fixed `random_state=42` for HistGradientBoosting;
- validation-based model selection; and
- row-count, missing-value, negative-prediction, and total-demand checks.

The selected forecast is stored in DuckDB table `forecast_output` and consumed by notebook 06.

## 15. Recommended monitoring

If the workflow is extended beyond this portfolio analysis, monitor:

- WAPE, MAE, and bias by week;
- performance by volume tier and borough;
- holiday versus non-holiday error;
- zero-demand prediction behavior;
- changes in zone-level demand distribution;
- missing or unseen zones and time periods; and
- the proportion of positioning rows requiring caution or manual review.

Retraining or redesign should be considered when error or bias rises consistently, geographic demand patterns shift, or additional years and operational supply data become available.
