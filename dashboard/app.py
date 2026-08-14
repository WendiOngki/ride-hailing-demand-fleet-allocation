"""
Ride-Hailing Demand & Fleet Allocation Analytics — Dashboard
Reads from the project's DuckDB warehouse (nyc_taxi.db) built in notebooks 01-06.

Run with:
    streamlit run app.py

Expected to live inside the project's /dashboard folder, one level above
where nyc_taxi.db sits at ../data/processed/nyc_taxi.db. Adjust DB_PATH
below if your folder structure differs.
"""

import duckdb
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

DB_PATH = "../data/processed/nyc_taxi.db"

st.set_page_config(page_title="Ride-Hailing Demand & Fleet Allocation", layout="wide")


# ----------------------------------------------------------------------
# Connection & cached data loaders
# ----------------------------------------------------------------------

@st.cache_resource
def get_connection():
    return duckdb.connect(DB_PATH, read_only=True)


@st.cache_data
def load_hourly_dow_heatmap():
    con = get_connection()
    return con.execute("""
        SELECT
            EXTRACT(HOUR FROM pickup_datetime) AS hour_of_day,
            ISODOW(pickup_datetime) AS day_of_week,
            COUNT(*) AS total_trip
        FROM fact_trip
        GROUP BY hour_of_day, day_of_week
        ORDER BY day_of_week, hour_of_day
    """).df()


@st.cache_data
def load_borough_list():
    con = get_connection()
    return con.execute("""
        SELECT DISTINCT Borough FROM dim_zone
        WHERE Borough IS NOT NULL AND Borough != 'N/A'
        ORDER BY Borough
    """).df()["Borough"].tolist()


@st.cache_data
def load_daily_trend():
    con = get_connection()
    return con.execute("""
        SELECT
            DATE_TRUNC('day', pickup_datetime) AS trip_date,
            COUNT(*) AS total_trip
        FROM fact_trip
        GROUP BY trip_date
        ORDER BY trip_date
    """).df()


@st.cache_data
def load_weekday_weekend():
    con = get_connection()
    return con.execute("""
        SELECT
            CASE WHEN ISODOW(pickup_datetime) IN (6, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type,
            COUNT(*) * 1.0 / COUNT(DISTINCT DATE_TRUNC('day', pickup_datetime)) AS avg_trip_per_day
        FROM fact_trip
        GROUP BY day_type
    """).df()


@st.cache_data
def load_forecast_output():
    con = get_connection()
    return con.execute("SELECT * FROM forecast_output").df()


@st.cache_data
def load_allocation_recommendation():
    con = get_connection()
    return con.execute("SELECT * FROM fleet_allocation_recommendation").df()


def calculate_wape(y_true, y_pred):
    return (y_true - y_pred).abs().sum() / y_true.abs().sum() * 100


def calculate_mape(y_true, y_pred):
    mask = y_true != 0
    return ((y_true[mask] - y_pred[mask]).abs() / y_true[mask].abs()).mean() * 100


# ----------------------------------------------------------------------
# Sidebar navigation
# ----------------------------------------------------------------------

st.sidebar.title("Ride-Hailing Analytics")
page = st.sidebar.radio(
    "Go to",
    ["Demand Heatmap", "Trend and Seasonality", "Forecast vs Actual", "Fleet Allocation Recommendation"]
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Data: NYC TLC HVFHS trip records, Jan-Dec 2024. "
    "Completed trips only — does not capture unmatched/cancelled demand. "
    "See project README for full limitations."
)


# ----------------------------------------------------------------------
# Page 1: Demand Heatmap
# ----------------------------------------------------------------------

if page == "Demand Heatmap":
    st.title("Demand Heatmap: Zone x Hour x Day")
    st.caption("Trip volume by hour of day and day of week, across all zones (2024).")

    df_heat = load_hourly_dow_heatmap()

    dow_labels = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
    df_heat["day_label"] = df_heat["day_of_week"].map(dow_labels)

    pivot = df_heat.pivot(index="day_label", columns="hour_of_day", values="total_trip")
    pivot = pivot.reindex(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])

    fig, ax = plt.subplots(figsize=(14, 5))
    sns.heatmap(pivot, cmap="Blues", ax=ax, cbar_kws={"label": "Total Trips"})
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("")
    st.pyplot(fig)

    st.markdown(
        "**Reading this chart:** darker cells indicate higher trip volume. "
        "Expect the darkest band around 17:00-19:00 on weekdays, and a broader "
        "elevated band on weekend evenings/nights."
    )


# ----------------------------------------------------------------------
# Page 2: Trend and Seasonality
# ----------------------------------------------------------------------

elif page == "Trend and Seasonality":
    st.title("Trend and Seasonality")

    df_daily = load_daily_trend()

    st.subheader("Daily Trip Volume Over 2024")
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.plot(df_daily["trip_date"], df_daily["total_trip"], color="#37474F", linewidth=1)
    ax.set_xlabel("Date")
    ax.set_ylabel("Total Trips")
    st.pyplot(fig)

    st.subheader("Weekday vs Weekend")
    df_wk = load_weekday_weekend()
    col1, col2 = st.columns(2)
    for col, row in zip([col1, col2], df_wk.itertuples()):
        col.metric(row.day_type, f"{row.avg_trip_per_day:,.0f} trips/day")

    st.caption(
        "Weekend average includes Saturday and Sunday; weekday average includes Monday-Friday. "
        "See notebook 04 for zone-level volatility and supply-demand proxy analysis."
    )


# ----------------------------------------------------------------------
# Page 3: Forecast vs Actual
# ----------------------------------------------------------------------

elif page == "Forecast vs Actual":
    st.title("Forecast vs Actual")
    st.caption("Model performance on the held-out test period (Nov 7 - Dec 31, 2024).")

    df_fc = load_forecast_output()

    wape = calculate_wape(df_fc["total_trip"], df_fc["model_pred"])
    mape = calculate_mape(df_fc["total_trip"], df_fc["model_pred"])

    col1, col2 = st.columns(2)
    col1.metric("WAPE (test set)", f"{wape:.2f}%")
    col2.metric("MAPE (test set)", f"{mape:.2f}%")

    st.subheader("Actual vs Forecast, Aggregated by Date")
    df_daily_fc = df_fc.groupby("trip_date")[["total_trip", "model_pred"]].sum().reset_index()

    fig, ax = plt.subplots(figsize=(14, 4))
    ax.plot(df_daily_fc["trip_date"], df_daily_fc["total_trip"], label="Actual", color="#37474F")
    ax.plot(df_daily_fc["trip_date"], df_daily_fc["model_pred"], label="Forecast", color="#B0BEC5", linestyle="--")
    ax.set_xlabel("Date")
    ax.set_ylabel("Total Trips")
    ax.legend()
    st.pyplot(fig)

    st.subheader("Performance by Zone Volume Tier")
    tier_rows = []
    for tier in ["Low", "Medium", "High"]:
        subset = df_fc[df_fc["volume_tier"] == tier]
        tier_rows.append({
            "Tier": tier,
            "WAPE (%)": round(calculate_wape(subset["total_trip"], subset["model_pred"]), 2),
            "MAPE (%)": round(calculate_mape(subset["total_trip"], subset["model_pred"]), 2),
        })
    st.table(pd.DataFrame(tier_rows))

    st.markdown(
        "**Note:** the model outperforms a simple historical-average baseline overall and "
        "most clearly in high-volume zones. In low-volume zones, performance is close to "
        "baseline — see model card for why this is an expected limitation, not a bug."
    )


# ----------------------------------------------------------------------
# Page 4: Fleet Allocation Recommendation
# ----------------------------------------------------------------------

elif page == "Fleet Allocation Recommendation":
    st.title("Fleet Allocation Recommendation")
    st.caption(
        "Relative allocation guidance per zone-hour, based on forecasted demand vs. "
        "historical average capacity. Not an absolute driver count."
    )

    df_alloc = load_allocation_recommendation()

    boroughs = ["All"] + sorted(df_alloc["Borough"].dropna().unique().tolist())
    selected_borough = st.selectbox("Filter by Borough", boroughs)

    recommendations = ["All"] + sorted(df_alloc["allocation_recommendation"].dropna().unique().tolist())
    selected_rec = st.selectbox("Filter by Recommendation", recommendations)

    df_filtered = df_alloc.copy()
    if selected_borough != "All":
        df_filtered = df_filtered[df_filtered["Borough"] == selected_borough]
    if selected_rec != "All":
        df_filtered = df_filtered[df_filtered["allocation_recommendation"] == selected_rec]

    st.subheader(f"Zone-Hour Recommendations ({len(df_filtered):,} rows)")
    st.dataframe(
        df_filtered[[
            "Zone", "Borough", "trip_date", "hour_of_day", "time_segment",
            "forecast_trip", "forecast_lower", "forecast_upper",
            "allocation_ratio_pct", "allocation_recommendation"
        ]].sort_values("allocation_ratio_pct", ascending=False),
        use_container_width=True,
        height=400,
    )

    st.markdown(
        "**Limitations:** allocation ratios are relative to each zone-hour's historical "
        "average, not absolute driver counts (this dataset has no driver-count data). "
        "Uncertainty intervals (forecast_lower-forecast_upper) widen for low-volume zones. "
        "This output is advisory and requires human review before operational use — "
        "see project README and model card for full limitations."
    )
