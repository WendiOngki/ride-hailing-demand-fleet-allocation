# Executive Memo: Ride-Hailing Demand & Fleet Allocation Analytics

**To:** Head of Operations, Regional Operations Managers
**From:** Analytics Team
**Re:** Demand patterns and fleet allocation guidance from 2024 trip data

---

## The Question We Set Out to Answer

Where and when is rider demand highest, how predictable is it, and how should we adjust driver allocation in response — using only the official trip records we have, without overstating what that data can tell us?

## What We Found

- **Demand has a strong, consistent rhythm.** Trips peak around 6 PM on weekdays and are lowest between 3–4 AM. Weekends see about 13% higher average daily trips than weekdays.
- **Manhattan dominates volume**, but the busiest *individual* zones by activity are the airports (JFK, LaGuardia) and Manhattan hubs like Times Square and Midtown.
- **Some zones are far more volatile than others.** A handful of zones (mostly park/recreation areas in Queens) swing wildly day to day; most residential zones are comparatively stable and predictable.
- **We built a forecasting model that beats a simple historical average**, but only reliably in busier zones. In low-volume zones, no model — ours included — meaningfully outperforms just looking at historical averages. That's not a flaw we can engineer away; it's a mathematical reality of predicting rare events.
- **We can now flag zone-hours where demand is trending meaningfully above or below their historical norm**, with an honest range of uncertainty attached — not a single "confident" number.

## What This Means for Allocation

We recommend using the accompanying zone-hour recommendations as a **directional signal** — "this zone-hour is running hot, consider shifting supply toward it" — rather than a precise headcount. For high-volume zones (airports, Manhattan core), confidence is reasonably strong. For low-volume zones, treat any single prediction with caution and lean on historical patterns and local judgment.

## What This Analysis Cannot Tell You

- **We don't know how much demand we're missing.** This data only records completed trips — riders who cancelled, were rejected, or never got matched to a driver aren't in it. Actual demand is very likely higher than what we measured, especially in undersupplied zones.
- **We can't tell you why demand shifted** — no pricing, promotion, or weather data was used, so we can describe patterns but not explain their causes.
- **We don't know actual driver counts per zone**, so all "supply" language here is a proxy based on trip activity, not real fleet utilization.
- **This is not a live system.** It reflects 2024 patterns and would need to be re-validated before being trusted for day-to-day dispatch decisions.

## Bottom Line

The data supports confident, data-backed conversations about *where and when* to focus driver supply — especially in our busiest zones. It does not yet support precise staffing numbers or claims about unmet demand, and any allocation decision should still involve a human in the loop.

*Full technical methodology, data limitations, and reproduction steps: see project README and model card.*
