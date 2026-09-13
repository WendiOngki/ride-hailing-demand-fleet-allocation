# Executive Memo — NYC Ride-Hailing Demand Forecasting & Demand-Based Fleet Positioning

|                              |                                                                                  |
| ---------------------------- | -------------------------------------------------------------------------------- |
| To                           | Operations Leadership                                                            |
| From                         | Analytics Team                                                                   |
| Historical period            | January–December 2024                                                            |
| Historical forecast scenario | 1–7 January 2025                                                                 |
| Subject                      | Completed-trip patterns, forecast performance, and relative positioning guidance |

## Decision Summary

Use the analytical output as an **hourly relative positioning signal**. It identifies which pickup zones account for larger shares of forecasted completed-trip workload within the same hour.

Do not treat the output as an exact vehicle requirement. The public data does not contain active-driver counts, available driver-hours, vehicles by zone, repositioning time/cost, or operational supply constraints.

## What the Historical Data Shows

The cleaned warehouse contains **239.43 million completed trips** from 2024.

- Average daily activity is approximately **630,214 trips on weekdays** and **714,525 on weekends**.
- The average peak hour is **18:00**, with approximately **38,609 trips per day** at that hour. The lowest is **03:00**, with approximately **9,740**.
- Manhattan contributes **38.87%** of recorded pickups, followed by Brooklyn at 26.38%, Queens at 20.92%, and the Bronx at 12.35%.
- LaGuardia Airport and JFK Airport are the busiest individual pickup zones by completed-trip count.
- Daily stability differs by zone. Among the busiest zones, East Village and Bushwick South vary more from day to day than East Chelsea and Times Square.
- The average completed trip is **5.08 miles** and **20.13 minutes**.

These findings show strong recurring geographic, hourly, and weekday patterns, but also meaningful differences in zone-level volatility.

## Forecasting Result

Three models were compared on November 2024 validation data:

| Candidate                             | Validation WAPE | Validation bias |
| ------------------------------------- | --------------: | --------------: |
| **Holiday-Aware Historical Baseline** |      **15.29%** |      **-1.71%** |
| HistGradientBoosting                  |          16.61% |           4.15% |
| Linear Regression                     |          18.37% |          -4.43% |

The Holiday-Aware Historical Baseline was selected because it produced the lowest validation WAPE. It uses recurring zone-hour-weekday patterns for regular dates and a pooled zone-hour pattern for US federal holidays.

On the untouched December test period, the selected model achieved:

- **WAPE:** 19.61%;
- **MAE:** 21.19 completed trips per zone-hour; and
- **bias:** -4.99%, indicating overall underprediction.

December errors were higher than November errors, particularly around the end-of-year period. The saved January 2025 output should therefore be interpreted as an out-of-time historical forecast scenario and planning demonstration rather than a current or real-time forecast.

## Positioning Guidance

The historical forecast scenario contains **44,016 rows** covering 168 hours and 262 zones from 1–7 January 2025.

For each zone-hour, notebook 06:

1. multiplies forecasted completed trips by historical average trip duration;
2. estimates completed-trip workload hours;
3. calculates each zone's share of the same hour's total workload;
4. ranks all 262 zones; and
5. assigns High, Medium, or Standard positioning priority.

Every forecast hour contains 262 zones, and the relative positioning shares sum to 100%.

Across the complete seven-day output:

| Review flag               |   Rows |  Share |
| ------------------------- | -----: | -----: |
| Standard use              | 25,056 | 56.92% |
| Use with caution          | 18,624 | 42.31% |
| Manual review recommended |    336 |  0.76% |

The review flags reflect forecast-volume-tier reliability, the specificity of the historical-duration estimate, and holiday status. New Year's Day is marked for cautious use because the holiday-aware model still relies on limited pooled holiday history.

## Recommended Use

- Review High-priority zones first when considering where operational attention may be needed.
- Use Medium-priority zones as the next coverage layer.
- Preserve service awareness in Standard and lower-volume zones rather than treating low forecast volume as permission to remove service.
- Give additional attention to low-volume zones, broader duration fallbacks, and holiday/event periods.
- Compare the recommendation with live supply, traffic, events, airport conditions, and local operational knowledge.

## What the Analysis Cannot Determine

1. **Total passenger demand:** only completed trips are observed.
2. **Unmet demand:** cancelled, rejected, unmatched, and abandoned requests are not fully represented.
3. **Exact vehicle requirements:** no fleet-size or active-driver information is available.
4. **Repositioning feasibility:** travel time, distance, and cost between positioning zones are not optimized.
5. **Why demand changes:** weather, events, pricing, promotions, traffic, and transit disruption are absent.
6. **Production readiness:** the workflow is notebook-based and does not include live monitoring or automated dispatch integration.

## Recommended Next Steps

1. Re-run notebooks 01–06 from fresh kernels to confirm end-to-end reproducibility.
2. Add additional years of history to improve seasonal and holiday estimation.
3. Add weather, events, airport schedules, traffic, and transit-disruption data.
4. Obtain operational supply inputs before attempting exact fleet allocation or optimization.
5. Monitor WAPE and bias by time period, borough, zone-volume tier, and holiday status.
6. Add minimum geographic-service constraints before using the output operationally.

## Bottom Line

The analysis provides a defensible estimate of short-horizon **completed-trip activity** and a transparent method for ranking **relative positioning priorities**. It can support planning discussions about where and when operational attention may be useful. It does not support exact staffing numbers, measurement of unmet demand, or fully optimized fleet allocation.

Technical details are available in the [README](../README.md) and [Model Card](MODEL_CARD.md).
