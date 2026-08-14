# Model Card — Ride-Hailing Demand Forecasting Model

Part of: *Ride-Hailing Demand & Fleet Allocation Analytics* (Project 1)

---

## Model Overview

| | |
|---|---|
| **Task** | Short-horizon demand forecasting — predict trip count per zone-hour |
| **Type** | Regression |
| **Algorithm** | Gradient Boosting Regressor (scikit-learn), 300 estimators, max depth 6, learning rate 0.05 |
| **Baseline compared against** | Historical average per (zone, hour-of-day, day-of-week) |
| **Training notebook** | `05_demand_forecasting.ipynb` |
| **Downstream use** | Feeds `06_fleet_allocation_logic.ipynb` for relative allocation recommendations |

## Intended Use

Estimate near-term ride-hailing trip demand at the zone-hour level, to inform **relative** fleet allocation guidance (e.g., "this zone-hour is trending 30% above its historical average"). Intended for exploratory/portfolio demonstration of a demand-forecasting pipeline — not validated for live operational dispatch decisions.

**Not intended for:** absolute driver-count staffing decisions, real-time dispatch automation, pricing decisions, or any use implying causal understanding of what drives demand changes.

## Training Data

- Source: `fact_trip` (DuckDB warehouse), aggregated to a zone × hour × date mart — 2,215,471 rows.
- Train period: 2024-01-01 to 2024-11-06 (1,882,991 rows).
- Test period: 2024-11-07 to 2024-12-31 (332,480 rows).
- **Split method:** rolling-origin (chronological), not random — train strictly precedes test in time, to avoid temporal leakage. This is a deliberately stricter standard than a random train/test split, and typically yields higher (more honest) error rates than a leaked random split would.

## Features

Built iteratively; final feature set:

| Feature | Description | Computed From |
|---|---|---|
| `zone_avg_trip` | Zone's overall average trip count (target-encoded) | Train set only |
| `zone_hour_avg` | Zone × hour-of-day average trip count | Train set only |
| `zone_dow_avg` | Zone × day-of-week average trip count | Train set only |
| `hour_of_day` | Hour (0–23) | Raw timestamp |
| `is_weekend` | Binary flag | Day-of-week |
| `avg_trip_miles`, `min_trip_miles`, `max_trip_miles` | Distance stats per zone-hour-date | `fact_trip` |
| `avg_trip_time` | Duration stat per zone-hour-date | `fact_trip` |
| `dow_*` (one-hot) | Day-of-week, one-hot encoded | Categorical, not ordinal |
| `seg_*` (one-hot) | Time-of-day segment (Late Night / Morning Rush / Midday / Evening Rush / Night) | Binned from hour |

**Note on `PULocationID`:** raw zone ID is intentionally **not** used as a numeric feature — an early iteration confirmed this produces meaningless results (WAPE 40.4%, MAPE 209%, including negative predictions), because zone IDs are categorical labels, not an ordinal scale. All zone information enters the model via target-encoded averages instead.

**Note on `avg_trip_miles`/`avg_trip_time`:** these are computed from the same zone-hour-date row being predicted, which introduces a mild same-day leakage (the model effectively knows the actual trip-distance profile of the day it's predicting demand for). This is a known simplification — a stricter version would use prior-period average distance instead. Flagged here for transparency; not yet corrected in this iteration.

## Evaluation

Metrics: **WAPE** (volume-weighted absolute percentage error) and **MAPE** (mean absolute percentage error), evaluated together — never accuracy or a single metric alone, per this project's metric contract.

### Overall (test set, Nov 7 – Dec 31, 2024)

| Model | WAPE | MAPE |
|---|---|---|
| Baseline (historical average) | 18.22% | 27.95% |
| Advanced (Gradient Boosting) | **17.43%** | **26.48%** |

### By zone volume tier

Zones split into Low/Medium/High tiers by historical average trip volume (train set), roughly equal-sized groups (88/87/87 zones).

| Tier | Baseline WAPE | Model WAPE | Baseline MAPE | Model MAPE |
|---|---|---|---|---|
| Low | 22.61% | 22.63% | 41.62% | 39.90% |
| Medium | 17.38% | 17.10% | 19.33% | 19.42% |
| High | 18.07% | **16.97%** | 24.32% | **21.52%** |

**Interpretation:** the model's improvement over baseline is concentrated in high-volume zones, where there is enough historical signal to learn meaningful patterns. In low-volume zones, the model does not reliably beat the baseline — this reflects the inherent unpredictability of sparse count data (a single-digit-trip zone-hour has high relative variance no matter the model), not a correctable modeling flaw.

## Development Iterations

Documented for transparency — this was not a first-try success:

| Iteration | Key change | WAPE | MAPE |
|---|---|---|---|
| 1 | Raw `PULocationID` as numeric feature | 40.36% | 208.99% |
| 2 | Target-encoded zone average, dropped raw ID | 21.96% | 36.23% |
| 3 | + distance/duration stats, one-hot day-of-week | 20.67% | 37.06% |
| 4 | + zone×hour and zone×day-of-week interaction features | 18.18% | 30.64% |
| 5 (final) | + min/max distance, time-of-day segments | **17.43%** | **26.48%** |

## Known Limitations

- Model does not reliably outperform a simple historical-average baseline in low-volume zones.
- Same-day trip-distance features introduce mild leakage (see Features section).
- Trained on a single year (2024) — no validation across multiple years or against structural shifts (e.g., new competitor entry, major fare changes, regulatory changes).
- No weather, event-calendar, or holiday features — these are plausible demand drivers not present in this iteration.
- Predictions are clipped at zero (trip counts cannot be negative) but otherwise unconstrained; no domain-specific caps applied.
- Does not model unmatched/cancelled demand — see project README limitations.

## Misuse Risks

- Should not be used to justify reducing driver presence in low-volume zones based on point predictions alone — uncertainty is wide there, and the model does not clearly outperform simpler methods in that regime.
- Should not be presented as validated for live operational dispatch without further testing against actual driver-supply data, which this project does not have access to.
- Ratio-based allocation recommendations (see `06_fleet_allocation_logic.ipynb`) are relative guidance, not absolute staffing targets, and require human review before any operational use.
