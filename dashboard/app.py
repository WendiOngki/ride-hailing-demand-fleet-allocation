"""Streamlit dashboard for the ride-hailing analytics project.

Run from the project root:
    streamlit run dashboard/app.py
"""

from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / 'data' / 'processed' / 'nyc_taxi.db'

st.set_page_config(
    page_title='Ride-Hailing Forecasting & Positioning',
    page_icon='🚕',
    layout='wide'
)


@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data(show_spinner=False)
def load_historical_summary():
    return get_connection().execute("""
        SELECT
            COUNT(*) AS completed_trips,
            COUNT(DISTINCT CAST(pickup_datetime AS DATE)) AS number_of_days,
            COUNT(DISTINCT PULocationID) AS pickup_zones,
            MIN(pickup_datetime) AS min_pickup,
            MAX(pickup_datetime) AS max_pickup
        FROM fact_trip
    """).df()


@st.cache_data(show_spinner=False)
def load_daily_trend():
    return get_connection().execute("""
        SELECT
            CAST(pickup_datetime AS DATE) AS demand_date,
            COUNT(*) AS completed_trips
        FROM fact_trip
        GROUP BY demand_date
        ORDER BY demand_date
    """).df()


@st.cache_data(show_spinner=False)
def load_weekday_weekend():
    return get_connection().execute("""
        SELECT
            CASE
                WHEN ISODOW(pickup_datetime) IN (6, 7) THEN 'Weekend'
                ELSE 'Weekday'
            END AS day_type,
            COUNT(DISTINCT CAST(pickup_datetime AS DATE)) AS number_of_days,
            COUNT(*) * 1.0
                / COUNT(DISTINCT CAST(pickup_datetime AS DATE))
                AS avg_completed_trips
        FROM fact_trip
        GROUP BY day_type
        ORDER BY day_type
    """).df()


@st.cache_data(show_spinner=False)
def load_hourly_heatmap():
    return get_connection().execute("""
        SELECT
            ISODOW(pickup_datetime) AS day_of_week,
            EXTRACT(HOUR FROM pickup_datetime)::INTEGER AS hour_of_day,
            COUNT(*) * 1.0
                / COUNT(DISTINCT CAST(pickup_datetime AS DATE))
                AS avg_completed_trips
        FROM fact_trip
        GROUP BY day_of_week, hour_of_day
        ORDER BY day_of_week, hour_of_day
    """).df()


@st.cache_data(show_spinner=False)
def load_model_evaluation():
    return get_connection().execute("""
        SELECT *
        FROM forecast_model_evaluation
    """).df()


@st.cache_data(show_spinner=False)
def load_tier_evaluation():
    return get_connection().execute("""
        SELECT *
        FROM forecast_test_tier_evaluation
        ORDER BY CASE volume_tier
            WHEN 'Low' THEN 1
            WHEN 'Medium' THEN 2
            WHEN 'High' THEN 3
        END
    """).df()


@st.cache_data(show_spinner=False)
def load_forecast():
    return get_connection().execute("""
        SELECT *
        FROM forecast_output
        ORDER BY forecast_time, LocationID
    """).df()


@st.cache_data(show_spinner=False)
def load_positioning():
    return get_connection().execute("""
        SELECT *
        FROM fleet_allocation_recommendation
        ORDER BY forecast_time, positioning_rank
    """).df()


def format_metric_table(dataframe):
    result = dataframe.copy()
    numeric_columns = result.select_dtypes(include='number').columns
    result[numeric_columns] = result[numeric_columns].round(2)
    return result


st.sidebar.title('Ride-Hailing Analytics')
page = st.sidebar.radio(
    'Navigation',
    [
        'Project Overview',
        'Historical Patterns',
        'Model Evaluation',
        '7-Day Forecast',
        'Positioning Guidance'
    ]
)

st.sidebar.divider()
st.sidebar.caption(
    'NYC TLC HVFHS completed trips, January–December 2024. '
    'The output estimates completed-trip activity, not total latent demand.'
)

if not DB_PATH.exists():
    st.error(f'Database not found: {DB_PATH}')
    st.info('Run notebooks 01–06 before starting the dashboard.')
    st.stop()


if page == 'Project Overview':
    st.title('Ride-Hailing Forecasting & Demand-Based Positioning')
    st.caption(
        'Historical completed-trip analysis, holiday-aware forecasting, '
        'and relative pickup-zone positioning guidance.'
    )

    with st.spinner('Loading project summary...'):
        summary = load_historical_summary().iloc[0]
        forecast = load_forecast()
        positioning = load_positioning()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Clean completed trips', f'{summary.completed_trips:,.0f}')
    col2.metric('Historical days', f'{summary.number_of_days:,.0f}')
    col3.metric('Forecast zone-hours', f'{len(forecast):,}')
    col4.metric('Actionable zones', f'{forecast["LocationID"].nunique():,}')

    st.subheader('Pipeline')
    st.markdown(
        '1. Acquire and verify 2024 NYC TLC trip files.  '
        '\n2. Audit timestamps, distance, duration, zones, and duplicates.  '
        '\n3. Build the DuckDB analytical warehouse.  '
        '\n4. Describe temporal and geographic completed-trip patterns.  '
        '\n5. Select and test the holiday-aware forecasting model.  '
        '\n6. Convert the forecast into relative positioning guidance.'
    )

    st.subheader('How to interpret the output')
    left, right = st.columns(2)
    left.success(
        '**Appropriate use:** compare expected completed-trip workload across '
        'zones within the same forecast hour.'
    )
    right.warning(
        '**Not supported:** exact driver counts, available fleet capacity, '
        'dispatch instructions, or measurement of unmet demand.'
    )

    review_share = (
        positioning['review_flag'].value_counts(normalize=True).mul(100)
    )
    st.caption(
        f'Standard-use positioning rows: '
        f'{review_share.get("Standard use", 0):.2f}% · '
        f'Use-with-caution rows: '
        f'{review_share.get("Use with caution", 0):.2f}% · '
        f'Manual-review rows: '
        f'{review_share.get("Manual review recommended", 0):.2f}%'
    )


elif page == 'Historical Patterns':
    st.title('Historical Completed-Trip Patterns')
    st.caption('Observed activity from the cleaned 2024 trip records.')

    with st.spinner('Aggregating historical patterns...'):
        daily = load_daily_trend()
        day_type = load_weekday_weekend()
        hourly = load_hourly_heatmap()

    weekday = day_type.loc[
        day_type['day_type'].eq('Weekday'), 'avg_completed_trips'
    ].iloc[0]
    weekend = day_type.loc[
        day_type['day_type'].eq('Weekend'), 'avg_completed_trips'
    ].iloc[0]

    col1, col2, col3 = st.columns(3)
    col1.metric('Weekday average', f'{weekday:,.0f} trips/day')
    col2.metric('Weekend average', f'{weekend:,.0f} trips/day')
    col3.metric('Weekend difference', f'{(weekend / weekday - 1) * 100:.1f}%')

    daily_chart = px.line(
        daily,
        x='demand_date',
        y='completed_trips',
        title='Daily Completed Trips in 2024',
        labels={
            'demand_date': 'Date',
            'completed_trips': 'Completed Trips'
        }
    )
    daily_chart.update_layout(hovermode='x unified')
    st.plotly_chart(daily_chart, use_container_width=True)

    day_labels = {
        1: 'Monday', 2: 'Tuesday', 3: 'Wednesday',
        4: 'Thursday', 5: 'Friday', 6: 'Saturday', 7: 'Sunday'
    }
    hourly['day_name'] = hourly['day_of_week'].map(day_labels)
    heatmap_data = hourly.pivot(
        index='day_name',
        columns='hour_of_day',
        values='avg_completed_trips'
    ).reindex(list(day_labels.values()))

    heatmap = px.imshow(
        heatmap_data,
        aspect='auto',
        color_continuous_scale='Blues',
        title='Average Completed Trips by Day and Hour',
        labels={
            'x': 'Hour of Day',
            'y': 'Day of Week',
            'color': 'Average Trips'
        }
    )
    st.plotly_chart(heatmap, use_container_width=True)


elif page == 'Model Evaluation':
    st.title('Forecast Model Evaluation')
    st.caption(
        'Models were selected on November 2024 validation data. '
        'December 2024 was retained for the final test.'
    )

    evaluation = load_model_evaluation()
    tier_evaluation = load_tier_evaluation()

    validation = evaluation[
        evaluation['evaluation_period'].eq('Validation')
    ].sort_values('WAPE (%)')
    test = evaluation[
        evaluation['evaluation_period'].eq('Test')
    ].iloc[0]

    st.success(
        f'Selected model: **{test["model"]}** — lowest validation WAPE.'
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Test WAPE', f'{test["WAPE (%)"]:.2f}%')
    col2.metric('Test MAE', f'{test["MAE"]:.2f}')
    col3.metric('Test MAPE nonzero', f'{test["MAPE nonzero (%)"]:.2f}%')
    col4.metric('Test bias', f'{test["Bias (%)"]:.2f}%')

    validation_chart = px.bar(
        validation,
        x='WAPE (%)',
        y='model',
        orientation='h',
        title='Validation WAPE by Candidate Model',
        labels={'model': 'Model'},
        text_auto='.2f'
    )
    validation_chart.update_layout(yaxis={'categoryorder': 'total descending'})
    st.plotly_chart(validation_chart, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader('Validation and test metrics')
        st.dataframe(
            format_metric_table(evaluation),
            hide_index=True,
            use_container_width=True
        )
    with col2:
        st.subheader('Test performance by volume tier')
        st.dataframe(
            format_metric_table(tier_evaluation),
            hide_index=True,
            use_container_width=True
        )

    st.info(
        'Negative test bias means the model underpredicted completed-trip volume '
        'overall. Low-volume zones have greater relative uncertainty.'
    )


elif page == '7-Day Forecast':
    st.title('Completed-Trip Forecast: 1–7 January 2025')
    st.caption(
        'Holiday-Aware Historical Baseline forecast for 262 actionable '
        'pickup zones and 168 consecutive hours.'
    )

    forecast = load_forecast()
    forecast['forecast_time'] = pd.to_datetime(forecast['forecast_time'])
    forecast['forecast_date'] = pd.to_datetime(
        forecast['forecast_date']
    ).dt.date

    borough_options = ['All'] + sorted(
        forecast['pickup_borough'].dropna().unique().tolist()
    )
    selected_borough = st.selectbox('Pickup borough', borough_options)

    filtered = forecast.copy()
    if selected_borough != 'All':
        filtered = filtered[
            filtered['pickup_borough'].eq(selected_borough)
        ]

    hourly_forecast = (
        filtered.groupby('forecast_time', as_index=False)
        .agg(forecast_completed_trips=('forecast_completed_trips', 'sum'))
    )
    peak = hourly_forecast.loc[
        hourly_forecast['forecast_completed_trips'].idxmax()
    ]

    col1, col2, col3 = st.columns(3)
    col1.metric(
        'Forecast completed trips',
        f'{filtered["forecast_completed_trips"].sum():,.0f}'
    )
    col2.metric('Selected zones', f'{filtered["LocationID"].nunique():,}')
    col3.metric(
        'Peak forecast hour',
        pd.Timestamp(peak['forecast_time']).strftime('%d %b, %H:%M')
    )

    forecast_chart = px.line(
        hourly_forecast,
        x='forecast_time',
        y='forecast_completed_trips',
        title='Hourly Forecasted Completed Trips',
        labels={
            'forecast_time': 'Forecast Time',
            'forecast_completed_trips': 'Forecast Completed Trips'
        }
    )
    forecast_chart.update_layout(hovermode='x unified')
    st.plotly_chart(forecast_chart, use_container_width=True)

    selected_time = st.selectbox(
        'Inspect one forecast hour',
        sorted(filtered['forecast_time'].unique()),
        format_func=lambda value: pd.Timestamp(value).strftime(
            '%A, %d %B %Y — %H:%M'
        )
    )
    zone_forecast = (
        filtered[filtered['forecast_time'].eq(selected_time)]
        .sort_values('forecast_completed_trips', ascending=False)
    )

    st.dataframe(
        zone_forecast[[
            'pickup_zone', 'pickup_borough', 'volume_tier',
            'is_holiday', 'forecast_completed_trips', 'model'
        ]].round({'forecast_completed_trips': 2}),
        hide_index=True,
        use_container_width=True,
        height=420
    )


elif page == 'Positioning Guidance':
    st.title('Relative Demand-Based Positioning Guidance')
    st.caption(
        'Recommended positioning shares are relative completed-trip workload '
        'shares within each forecast hour—not vehicle counts or fleet capacity.'
    )

    positioning = load_positioning()
    positioning['forecast_time'] = pd.to_datetime(
        positioning['forecast_time']
    )
    positioning['forecast_date'] = pd.to_datetime(
        positioning['forecast_date']
    ).dt.date

    date_options = sorted(positioning['forecast_date'].unique())
    selected_date = st.selectbox('Forecast date', date_options)
    selected_hour = st.slider('Hour of day', 0, 23, 18)
    selected_time = pd.Timestamp(selected_date) + pd.Timedelta(
        hours=selected_hour
    )

    full_hour = positioning[
        positioning['forecast_time'].eq(selected_time)
    ].copy()

    if full_hour.empty:
        st.warning('No positioning data is available for the selected hour.')
        st.stop()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        'Forecast completed trips',
        f'{full_hour["forecast_completed_trips"].sum():,.0f}'
    )
    col2.metric(
        'Forecast workload',
        f'{full_hour["forecasted_completed_trip_hours"].sum():,.1f} hours'
    )
    col3.metric(
        'Highest zone share',
        f'{full_hour["recommended_positioning_share_pct"].max():.2f}%'
    )
    col4.metric(
        'Rows requiring caution',
        f'{full_hour["review_flag"].ne("Standard use").sum():,}'
    )

    filter_col1, filter_col2, filter_col3 = st.columns(3)
    borough_options = ['All'] + sorted(
        full_hour['pickup_borough'].dropna().unique().tolist()
    )
    priority_options = ['All', 'High', 'Medium', 'Standard']
    review_options = ['All'] + sorted(
        full_hour['review_flag'].dropna().unique().tolist()
    )

    selected_borough = filter_col1.selectbox(
        'Pickup borough', borough_options, key='positioning_borough'
    )
    selected_priority = filter_col2.selectbox(
        'Positioning priority', priority_options
    )
    selected_review = filter_col3.selectbox('Review flag', review_options)

    filtered = full_hour.copy()
    if selected_borough != 'All':
        filtered = filtered[
            filtered['pickup_borough'].eq(selected_borough)
        ]
    if selected_priority != 'All':
        filtered = filtered[
            filtered['positioning_priority'].eq(selected_priority)
        ]
    if selected_review != 'All':
        filtered = filtered[
            filtered['review_flag'].eq(selected_review)
        ]

    show_all = st.checkbox('Visualize all matching zones', value=False)
    chart_data = filtered if show_all else filtered.head(30)

    priority_colors = {
        'High': '#D95F02',
        'Medium': '#E6AB02',
        'Standard': '#7570B3'
    }
    positioning_chart = px.bar(
        chart_data,
        x='positioning_rank',
        y='recommended_positioning_share_pct',
        color='positioning_priority',
        hover_name='pickup_zone',
        hover_data={
            'pickup_borough': True,
            'forecast_completed_trips': ':.2f',
            'forecasted_completed_trip_hours': ':.2f',
            'recommended_positioning_share_pct': ':.3f',
            'positioning_rank': True
        },
        color_discrete_map=priority_colors,
        category_orders={
            'positioning_priority': ['High', 'Medium', 'Standard']
        },
        title=f'Positioning Share — {selected_time:%d %B %Y, %H:%M}',
        labels={
            'positioning_rank': 'Zone Positioning Rank',
            'recommended_positioning_share_pct': 'Positioning Share (%)',
            'positioning_priority': 'Priority'
        }
    )
    positioning_chart.update_layout(bargap=0)
    st.plotly_chart(positioning_chart, use_container_width=True)

    st.dataframe(
        filtered[[
            'positioning_rank', 'pickup_zone', 'pickup_borough',
            'forecast_completed_trips', 'historical_avg_trip_minutes',
            'forecasted_completed_trip_hours',
            'recommended_positioning_share_pct', 'positioning_priority',
            'forecast_reliability', 'duration_reliability', 'review_flag'
        ]].round({
            'forecast_completed_trips': 2,
            'historical_avg_trip_minutes': 2,
            'forecasted_completed_trip_hours': 2,
            'recommended_positioning_share_pct': 3
        }),
        hide_index=True,
        use_container_width=True,
        height=450
    )

    st.warning(
        'Use these shares as directional planning evidence only. The project '
        'does not observe active drivers, available vehicles, repositioning '
        'time, repositioning cost, or unmet passenger requests.'
    )
