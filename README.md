# Weather-pipeline-project
End-to-End Weather Data Engineering Pipeline

## Overview

This project is an end-to-end weather data engineering pipeline for weather trends and outdoor planning in Louisville. It extracts forecast data from the Open-Meteo API, transforms and cleans the JSON response with Python, loads the data into Microsoft SQL Server, and keeps CSV files as backup snapshots for portability and reproducibility. A Dash dashboard then reads the refreshed SQL data to display weather trends, KPI cards, and outdoor planning insights.

## Project Goals

- Extract hourly weather data from the Open-Meteo REST API using Python.
- Clean, validate, and reshape the raw JSON into structured tables.
- Load transformed weather data into Microsoft SQL Server.
- Save CSV backups for inspection and recovery.
- Build an interactive Dash dashboard for weather trends and outdoor planning.
- Refresh the pipeline automatically on a scheduled basis.

## Data Flow

1. Open-Meteo provides hourly and daily forecast data in JSON format.
2. Python scripts call the API using selected coordinates and forecast variables.
3. The ETL process validates, flattens, and cleans the response.
4. Cleaned data is loaded into Microsoft SQL Server.
5. A CSV copy is saved as a backup snapshot.
6. Dash reads the SQL Server tables and renders charts, KPI cards, and planning indicators.

## Technologies Used

- Python
- requests
- pandas
- pyodbc
- Microsoft SQL Server
- Dash
- Plotly
- Dash Bootstrap Components

## ETL Workflow

### Extract
Python scripts send REST requests to Open-Meteo using selected coordinates, forecast ranges, and weather variables.

### Transform
The JSON response is validated, flattened into tables, timestamps are standardized, missing values are handled, and useful derived fields are created.

### Load
Transformed records are loaded into Microsoft SQL Server for dashboard access. CSV files are also written as backup copies.

### Visualize
Dash callbacks connect filters and charts so users can explore forecast trends and planning conditions interactively.

## Storage Design

The project uses a two-layer storage design. Microsoft SQL Server is the primary relational store used by the dashboard, while CSV files preserve cleaned snapshots for portability and reproducibility.

## Dashboard Features

- KPI cards for current temperature, rainfall probability, and wind conditions.
- Hourly and daily temperature trend charts.
- Precipitation visualizations.
- A simple outdoor planning panel that flags favorable, cautionary, or poor weather conditions based on forecast thresholds.

## Outdoor Planning Logic

The dashboard classifies weather into three categories:

- Favorable: suitable for outdoor activity.
- Caution: mixed conditions; use judgment.
- Poor: unfavorable outdoor conditions.

This classification can use temperature, precipitation, wind speed, cloud cover, rainfall probability, and weather code values from the forecast data.

## How to Run

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd <your-repo-folder>
```

### 2. Create a virtual environment

**Windows**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure SQL Server

Update your connection settings for Microsoft SQL Server in the application script or environment variables.

### 5. Run the Dash app

```bash
python app.py
```

If port 8050 is busy, run the app on another port such as 8051.

## Dependencies

Example `requirements.txt`:

```txt
dash
plotly
pandas
pyodbc
requests
dash-bootstrap-components
python-dotenv
```

## Business Insights

This dashboard turns raw weather forecasts into decision-ready information. It helps users identify favorable outdoor windows, monitor rainfall risk, compare conditions over time, and understand how wind or humidity may affect planning. The SQL-backed design also supports reliable refreshes, so the dashboard reflects the latest available weather data.

