import pandas as pd
import pyodbc
from dash import Dash, dcc, html, Input, Output, State, callback_context, no_update
import plotly.express as px
import dash_bootstrap_components as dbc

# ========================================================
# 1. DATABASE CONFIGURATION
# ========================================================
SERVER = "SERVER_NAME"
DATABASE = "WeatherPipelineDB"
DRIVER = "{ODBC Driver 17 for SQL Server}"

def get_connection():
    conn_str = (
        f"DRIVER={DRIVER};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)

import pandas as pd
import pyodbc
from dash import Dash, dcc, html, Input, Output, callback_context
import plotly.express as px
import dash_bootstrap_components as dbc

# =========================================================
# 2. OPTIONAL ETL REFRESH HOOK
# =========================================================
def run_etl_refresh():
    # Example:
    # from my_etl_script import run_pipeline
    # run_pipeline()
    pass

# =========================================================
# 3. WEATHER CODE + OUTDOOR PLANNING HELPERS
# =========================================================
def weather_code_description(code):
    code_map = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow fall",
        73: "Moderate snow fall",
        75: "Heavy snow fall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }
    return code_map.get(code, "Unknown weather condition")

def classify_outdoor_condition(row):
    temp = row.get("temperature")
    precip = row.get("precipitation", 0)
    rain_prob = row.get("rainfall_probability", 0)
    wind = row.get("wind_speed", 0)
    cloud = row.get("cloud_cover", 0)
    code = row.get("weather_code")

    poor_codes = {65, 67, 75, 82, 86, 95, 96, 99}
    caution_codes = {2, 3, 45, 48, 51, 53, 55, 56, 57, 61, 63, 66, 71, 73, 77, 80, 81, 85}

    if (
        code in poor_codes
        or (pd.notna(temp) and (temp < 45 or temp > 90))
        or (pd.notna(precip) and precip >= 0.15)
        or (pd.notna(rain_prob) and rain_prob >= 70)
        or (pd.notna(wind) and wind >= 20)
    ):
        return "Poor", "danger", "Outdoor conditions are unfavorable."

    elif (
        code in caution_codes
        or (pd.notna(temp) and (temp < 55 or temp > 85))
        or (pd.notna(precip) and precip > 0)
        or (pd.notna(rain_prob) and rain_prob >= 35)
        or (pd.notna(wind) and wind >= 12)
        or (pd.notna(cloud) and cloud >= 85)
    ):
        return "Caution", "warning", "Conditions are mixed; plan with caution."

    return "Favorable", "success", "Weather looks suitable for outdoor activity."

# =========================================================
# 4. QUERY REFRESHED DATA FROM SQL SERVER
# =========================================================
def load_weather_data():
    query = """
    SELECT
        l.location_name,
        w.forecast_timestamp,
        CAST(w.forecast_timestamp AS DATE) AS forecast_date,
        w.temperature,
        w.humidity,
        w.wind_speed,
        w.cloud_cover,
        w.precipitation,
        w.rainfall_probability,
        w.weather_code
    FROM dbo.weather_observation w
    INNER JOIN dbo.location l
        ON w.location_id = l.location_id
    ORDER BY w.forecast_timestamp
    """
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()

    df["forecast_timestamp"] = pd.to_datetime(df["forecast_timestamp"])
    df["forecast_date"] = pd.to_datetime(df["forecast_date"])
    return df

# =========================================================
# 5. APP SETUP
# =========================================================
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.title = "Louisville Weather Dashboard"

# =========================================================
# 6. REUSABLE KPI CARD
# =========================================================
def kpi_card(title, value, subtitle, color):
    return dbc.Card(
        dbc.CardBody([
            html.Div(title, className="text-muted", style={"fontSize": "0.9rem", "marginBottom": "6px"}),
            html.H3(value, className="mb-1", style={"fontWeight": "700"}),
            html.Div(subtitle, className="text-muted", style={"fontSize": "0.8rem"})
        ]),
        className="shadow-sm h-100",
        style={
            "borderLeft": f"6px solid {color}",
            "borderRadius": "14px"
        }
    )

# =========================================================
# 7. LAYOUT
# =========================================================
app.layout = dbc.Container([
    dcc.Interval(id="refresh-interval", interval=5 * 60 * 1000, n_intervals=0),
    dcc.Store(id="refresh-trigger", data={"last_refresh": 0}),

    dbc.Row([
        dbc.Col([
            html.H2("Louisville Weather Dashboard", className="mt-4 mb-1"),
            html.P(
                "Interactive hourly weather monitoring dashboard powered by refreshed SQL Server data.",
                className="text-muted mb-0"
            )
        ], md=8),
        dbc.Col([
            html.Div(
                id="refresh-status",
                className="text-end text-muted mt-4",
                style={"fontSize": "0.9rem"}
            )
        ], md=4)
    ], className="mb-4"),

    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Location", className="fw-bold"),
                    dcc.Dropdown(
                        id="location-filter",
                        multi=False,
                        placeholder="Select location"
                    )
                ], md=4),

                dbc.Col([
                    html.Label("Date Range", className="fw-bold"),
                    dcc.DatePickerRange(
                        id="date-filter",
                        display_format="YYYY-MM-DD"
                    )
                ], md=5),

                dbc.Col([
                    html.Label("Actions", className="fw-bold"),
                    dbc.Button(
                        "Refresh Data",
                        id="refresh-button",
                        color="primary",
                        className="w-100"
                    )
                ], md=3)
            ])
        ])
    ], className="shadow-sm mb-4", style={"borderRadius": "14px"}),

    dbc.Row([
        dbc.Col(html.Div(id="kpi-latest-temp"), md=4),
        dbc.Col(html.Div(id="kpi-avg-humidity"), md=4),
        dbc.Col(html.Div(id="kpi-total-precip"), md=4)
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(html.Div(id="planning-panel"), md=12)
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Hourly Temperature Trend", className="fw-bold"),
                dbc.CardBody(dcc.Graph(id="temperature-chart"))
            ], className="shadow-sm h-100", style={"borderRadius": "14px"})
        ], md=8),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Precipitation Probability Trend", className="fw-bold"),
                dbc.CardBody(dcc.Graph(id="rain-prob-chart"))
            ], className="shadow-sm h-100", style={"borderRadius": "14px"})
        ], md=4)
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Hourly Precipitation", className="fw-bold"),
                dbc.CardBody(dcc.Graph(id="precipitation-chart"))
            ], className="shadow-sm h-100", style={"borderRadius": "14px"})
        ], md=6),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Humidity vs Wind Speed", className="fw-bold"),
                dbc.CardBody(dcc.Graph(id="humidity-wind-chart"))
            ], className="shadow-sm h-100", style={"borderRadius": "14px"})
        ], md=6)
    ], className="mb-4")
], fluid=True, style={
    "backgroundColor": "#f4f6f9",
    "minHeight": "100vh",
    "paddingBottom": "30px",
    "paddingLeft": "22px",
    "paddingRight": "22px"
})

# =========================================================
# 8. REFRESH BUTTON / AUTO REFRESH TRIGGER
# =========================================================
@app.callback(
    Output("refresh-trigger", "data"),
    Output("refresh-status", "children"),
    Input("refresh-button", "n_clicks"),
    Input("refresh-interval", "n_intervals"),
    prevent_initial_call=False
)
def trigger_refresh(n_clicks, n_intervals):
    trigger = callback_context.triggered[0]["prop_id"].split(".")[0] if callback_context.triggered else "refresh-interval"

    if trigger == "refresh-button":
        run_etl_refresh()
        return (
            {"last_refresh": n_clicks or 0},
            "Data refreshed manually from SQL Server."
        )

    return (
        {"last_refresh": -(n_intervals or 0)},
        "Dashboard auto-refreshes every 5 minutes."
    )

# =========================================================
# 9. INITIALIZE FILTER OPTIONS
# =========================================================
@app.callback(
    Output("location-filter", "options"),
    Output("location-filter", "value"),
    Output("date-filter", "start_date"),
    Output("date-filter", "end_date"),
    Input("refresh-trigger", "data")
)
def initialize_filters(refresh_data):
    df = load_weather_data()

    if df.empty:
        return [], None, None, None

    location_options = [{"label": x, "value": x} for x in sorted(df["location_name"].dropna().unique())]
    default_location = location_options[0]["value"] if location_options else None

    start_date = df["forecast_date"].min().date()
    end_date = df["forecast_date"].max().date()

    return location_options, default_location, start_date, end_date

# =========================================================
# 10. MAIN DASHBOARD CALLBACK
# =========================================================
@app.callback(
    Output("kpi-latest-temp", "children"),
    Output("kpi-avg-humidity", "children"),
    Output("kpi-total-precip", "children"),
    Output("planning-panel", "children"),
    Output("temperature-chart", "figure"),
    Output("rain-prob-chart", "figure"),
    Output("precipitation-chart", "figure"),
    Output("humidity-wind-chart", "figure"),
    Input("location-filter", "value"),
    Input("date-filter", "start_date"),
    Input("date-filter", "end_date"),
    Input("refresh-trigger", "data")
)
def update_dashboard(location_value, start_date, end_date, refresh_data):
    df = load_weather_data()

    if location_value:
        df = df[df["location_name"] == location_value]

    if start_date:
        df = df[df["forecast_date"] >= pd.to_datetime(start_date)]

    if end_date:
        df = df[df["forecast_date"] <= pd.to_datetime(end_date)]

    if df.empty:
        empty_fig = px.line(title="No data available for selected filters")
        empty_fig.update_layout(template="plotly_white")
        return (
            kpi_card("Latest Temperature", "N/A", "No matching records", "#0d6efd"),
            kpi_card("Average Humidity", "N/A", "No matching records", "#17a2b8"),
            kpi_card("Total Precipitation", "N/A", "No matching records", "#198754"),
            dbc.Alert(
                "No planning guidance available for the selected filters.",
                color="secondary",
                className="shadow-sm",
                style={"borderRadius": "14px"}
            ),
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig
        )

    latest_row = df.sort_values("forecast_timestamp").iloc[-1]

    latest_temp = f"{latest_row['temperature']:.1f} °F" if pd.notna(latest_row["temperature"]) else "N/A"
    avg_humidity = f"{df['humidity'].mean():.1f} %" if df["humidity"].notna().any() else "N/A"
    total_precip = f"{df['precipitation'].sum():.2f} in" if df["precipitation"].notna().any() else "N/A"

    latest_temp_card = kpi_card("Latest Temperature", latest_temp, "Most recent hourly forecast", "#0d6efd")
    avg_humidity_card = kpi_card("Average Humidity", avg_humidity, "Across selected records", "#17a2b8")
    total_precip_card = kpi_card("Total Precipitation", total_precip, "Accumulated over selected period", "#198754")

    planning_status, planning_color, planning_message = classify_outdoor_condition(latest_row)
    weather_desc = weather_code_description(latest_row["weather_code"]) if pd.notna(latest_row["weather_code"]) else "Unknown weather condition"

    planning_panel = dbc.Alert([
        html.H5(f"Outdoor Planning Status: {planning_status}", className="mb-1"),
        html.Div(planning_message, className="mb-2"),
        html.Small(
            f"Weather: {weather_desc} | "
            f"Temp: {latest_row['temperature']:.1f} °F | "
            f"Rain Prob: {latest_row['rainfall_probability']:.0f}% | "
            f"Wind: {latest_row['wind_speed']:.1f} mph | "
            f"Cloud Cover: {latest_row['cloud_cover']:.0f}%"
        )
    ], color=planning_color, className="shadow-sm", style={"borderRadius": "14px"})

    fig_temp = px.line(
        df,
        x="forecast_timestamp",
        y="temperature",
        title="Temperature Over Time",
        markers=True
    )
    fig_temp.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=55, b=20))
    fig_temp.update_xaxes(title="Forecast Timestamp")
    fig_temp.update_yaxes(title="Temperature (°F)")

    fig_rain_prob = px.line(
        df,
        x="forecast_timestamp",
        y="rainfall_probability",
        title="Rainfall Probability Over Time",
        markers=True
    )
    fig_rain_prob.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=55, b=20))
    fig_rain_prob.update_xaxes(title="Forecast Timestamp")
    fig_rain_prob.update_yaxes(title="Rainfall Probability (%)")

    fig_precip = px.bar(
        df,
        x="forecast_timestamp",
        y="precipitation",
        title="Precipitation by Hour"
    )
    fig_precip.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=55, b=20))
    fig_precip.update_xaxes(title="Forecast Timestamp")
    fig_precip.update_yaxes(title="Precipitation (inches)")

    fig_scatter = px.scatter(
        df,
        x="humidity",
        y="wind_speed",
        color="temperature",
        color_continuous_scale="Blues",
        hover_data=["forecast_timestamp", "precipitation", "rainfall_probability", "weather_code"],
        title="Humidity vs Wind Speed"
    )
    fig_scatter.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=55, b=20))
    fig_scatter.update_xaxes(title="Humidity (%)")
    fig_scatter.update_yaxes(title="Wind Speed (mph)")

    return (
        latest_temp_card,
        avg_humidity_card,
        total_precip_card,
        planning_panel,
        fig_temp,
        fig_rain_prob,
        fig_precip,
        fig_scatter
    )

# =========================================================
# 11. RUN APP
# =========================================================
if __name__ == "__main__":
    app.run(debug=True, port=8051)
