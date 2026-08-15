# Executive Memo — Ride-Hailing Completed-Trip Forecasting & Positioning

**To:** Operations Leadership<br>
**From:** Analytics Team<br>
**Subject:** Where and when completed-trip activity concentrates, and how the result can support relative fleet positioning<br>
**Analysis period:** January–December 2024<br>
**Forecast period:** 1–7 January 2025

## Executive decision

Use the project output as an **hourly relative positioning signal**: it indicates which pickup zones should receive a larger or smaller share of operational attention based on forecasted completed-trip workload.

Do **not** interpret the output as an exact vehicle requirement. The source data does not contain active-driver counts, available driver-hours, vehicles by zone, repositioning time or cost, or other supply constraints.

## Business question

The analysis addresses three questions:

1. Where and when does completed-trip activity concentrate?
2. How accurately can zone-hour completed trips be forecast from 2024 history?
3. How can the forecast be converted into transparent, relative positioning priorities without overstating the available data?

## What the 2024 data shows

- The cleaned dataset contains **239.43 million completed trips** across 262 actionable pickup zones.
- Average daily activity is approximately **714,525 trips on weekends** and **630,214 on weekdays**, making weekends about **13.4% higher** on average.
- The busiest average hour is **18:00**, with approximately **38,609 trips per day** at that hour. The lowest is **03:00**, with approximately **9,740**.
- **Manhattan accounts for 38.87%** of recorded pickups, followed by Brooklyn at 26.38%, Queens at 20.92%, and the Bronx at 12.35%.
- LaGuardia Airport and JFK Airport are the two busiest individual pickup zones. Other major activity centres include the East Village, Crown Heights North, Times Square, Midtown Center, and TriBeCa/Civic Center.
- High volume does not always mean high instability. East Chelsea and Times Square combine high activity with relatively stable daily patterns, while East Village and Bushwick South show greater day-to-day variability.

These results indicate a strong recurring combination of zone, hour, and day-of-week patterns, but the variability is not uniform across the city.

## Forecasting result

Three approaches were compared using a chronological split:

| Candidate                             | Validation WAPE | Validation bias |
| ------------------------------------- | --------------: | --------------: |
| **Holiday-Aware Historical Baseline** |      **15.29%** |      **-1.71%** |
| HistGradientBoosting                  |          16.61% |           4.15% |
| Linear Regression                     |          18.37% |          -4.43% |

The **Holiday-Aware Historical Baseline** was selected because it produced the lowest validation error. It forecasts regular dates from the historical average for the same pickup zone, hour, and day of week. Federal holidays use a separate pooled holiday pattern.

This result is operationally useful: a transparent historical model performed better than the more complex alternatives. Greater model complexity was therefore not justified by the observed validation performance.

On the untouched December test period, the selected model achieved:

- **WAPE:** 19.61%;
- **MAE:** 21.19 trips per zone-hour; and
- **bias:** -4.99%, indicating overall underprediction.

The weaker December result shows that year-end activity is more difficult to represent with only one year of historical data. Forecasts should therefore be treated as estimates with measurable uncertainty, not exact future counts.

## Positioning recommendation

The final forecast contains **44,016 zone-hour rows** for 1–7 January 2025: 168 hours across 262 zones.

For every zone-hour, forecasted completed trips are converted into a completed-trip workload proxy using historical average trip duration. Each zone's workload is then divided by the total workload forecast for the same hour.

The resulting percentage answers:

> Of all forecasted completed-trip workload in this hour, what relative share is associated with this pickup zone?

Zones are labelled **High**, **Medium**, or **Standard** positioning priority based on cumulative workload share. The accompanying reliability and review flags identify results that require greater caution because of forecast error, sparse demand, broader duration fallbacks, or holiday conditions.

Recommended operational use:

- use High-priority zones as the first locations to examine for additional positioning attention;
- use Medium-priority zones as the second layer of coverage;
- retain minimum service awareness in Standard-priority and low-volume zones;
- compare recommendations with live conditions and local operational knowledge; and
- manually review holiday, low-reliability, and fallback-based recommendations.

## Important interpretation limits

1. **Completed trips are not total passenger demand.** Cancelled, rejected, unmatched, and unobserved requests are absent.
2. **The recommendation is relative, not absolute.** A 2% positioning share does not mean that exactly 2% of all active vehicles must be sent to that zone.
3. **No direct supply data is available.** The analysis cannot measure spare capacity, driver availability, or whether repositioning is feasible.
4. **External demand drivers are missing.** Weather, events, airport schedules, promotions, pricing, traffic, and transit disruption are not included.
5. **Holiday evidence is limited.** Only one year is available, so federal holidays are pooled rather than modelled individually.
6. **The workflow is analytical, not real time.** It must be refreshed and revalidated before operational deployment.

## Recommended next steps

1. Use the current output as a planning and portfolio prototype, not an automated dispatch rule.
2. Track WAPE and bias by week, demand tier, borough, and holiday status.
3. Add multiple years of trip history to improve holiday and seasonal estimation.
4. Add weather, event, airport, traffic, and transit-disruption data where available.
5. Obtain operational supply inputs—active drivers, available driver-hours, vehicles by zone, and repositioning time/cost—before developing a true fleet-capacity or optimization model.
6. Include minimum geographic-service constraints so that low-volume communities are not automatically deprioritized.

## Bottom line

The project provides a defensible forecast of **completed-trip activity** and a transparent way to rank **relative zone-positioning priorities**. It supports better conversations about where and when operational attention may be needed. It does not yet support exact staffing numbers, claims about unmet demand, or fully optimized fleet allocation.

Technical methodology, validation results, limitations, and reproduction steps are documented in `README.md` and `MODEL_CARD.md`.
