# End-to-End Weather Data Engineering Pipeline for Weather Trends and Outdoor Planning in Louisville

## Project Proposal


## Introduction / Background

Weather influences transportation, recreation, event planning, and everyday decisions, yet raw forecast data from public APIs is often difficult for nontechnical users to explore directly. A practical pipeline that transforms weather API responses into clean, queryable datasets and interactive dashboards can make forecast information easier to understand and use. The project is relevant for residents, commuters, outdoor planners, and local organizations that need a reliable way to monitor temperature, rainfall, wind, and general weather patterns when planning activities.

## Problem Statement

Although weather forecast data is publicly available, many users and analysts lack an automated system to consistently retrieve the data, clean the JSON structure, store it in a usable format, and present it via an interactive dashboard for trend analysis and outdoor planning. This creates inefficiencies in identifying useful patterns such as rainy days, heat spikes, or favorable conditions for outdoor activities.

## Objectives

- Extract hourly weather data from the Open-Meteo REST API using Python.
- Build an interactive dashboard in Dash to display weather trends and outdoor planning insights.
- Present a small set of decision-ready visualizations such as temperature trends, rainfall outlooks, and favorable outdoor-condition indicators.
- Create a repeatable workflow that can be refreshed automatically on a daily schedule.

## Methodology / Technical Approach

### API or Data Source

The project uses the Open-Meteo Forecast API as the primary data source. The API accepts latitude, longitude, and optional parameters and returns hourly and daily forecast data in JSON format, including temperature, humidity, wind speed, cloud cover, and precipitation.

### Tools and Technologies

- Python for ETL scripting and orchestration.
- requests for API communication.
- pandas for parsing, cleaning, and reshaping JSON data.
- pyodbc for database connection and loading.
- Microsoft SQL Server for local relational storage.
- Dash and Plotly for interactive visualization and dashboard controls.

### ETL Workflow Design

1. Extract: Python scripts send REST requests to Open-Meteo using selected coordinates, forecast ranges, and weather variables.
2. Transform: JSON responses are validated, flattened into tables, and cleaned by standardizing timestamps, renaming columns, and handling missing values.
3. Load: The transformed data is stored in CSV files for portability and in Microsoft SQL Server tables for efficient querying by the dashboard.
4. Visualize: Dash callbacks connect filters and charts so users can interactively explore forecast trends and planning conditions.

### Storage Approach

A two-layer storage design is used for simplicity and reliability. CSV files preserve cleaned data snapshots for inspection and reproducibility, while Microsoft SQL Server supports structured queries and dashboard access.

### Data Cleaning Techniques

Planned cleaning steps include parsing timestamps, validating expected weather fields, converting variables to the appropriate data types, checking for duplicates, and creating derived variables as needed.

### Scheduling or Automation Ideas

A scheduled Python task can refresh the pipeline once per day, retrieving the latest forecast and reloading the cleaned outputs into CSV and Microsoft SQL Server. Dash can then read the updated data and display current results without manual file preparation.

### Visualization Strategy

The dashboard will prioritize a small number of polished visual outputs. Planned components include:

- KPI cards for current temperature, rainfall probability, and wind conditions.
- A line chart for hourly and daily temperature trends.
- A bar chart for precipitation totals.
- A simple outdoor planning panel that flags favorable, cautionary, or poor weather conditions based on forecast thresholds.

## ETL Architecture Diagram

The ETL architecture shows Open-Meteo as the source API, Python as the ETL layer, Microsoft SQL Server as the primary database, CSV as the backup output, and Dash as the visualization layer. A scheduled refresh can trigger the pipeline on a daily or on-demand basis.

## Timeline

| Week | Planned Activities |
|---|---|
| Week 1 | Define project scope, review Open-Meteo documentation, select location(s), and design the pipeline workflow. |
| Week 2 | Build Python extraction scripts, test API responses, and save raw or initial cleaned weather data. |
| Week 3 | Transform JSON into structured tables with pandas and load data into CSV and Microsoft SQL Server. |
| Week 4 | Develop the Dash dashboard, including filters, KPI cards, and trend charts with interactive callbacks. |
| Week 5 | Test the full pipeline, automate refresh tasks, refine visuals, and prepare the final report and presentation demo. |

## Expected Outcomes

At the end of the project, the completed system will produce a working end-to-end weather data engineering pipeline that begins with REST API extraction and ends with an interactive dashboard for weather trends and outdoor planning. The project will demonstrate a complete ETL workflow, reliable data storage, and a clear visualization layer that helps users interpret weather conditions more effectively.

Expected final deliverables include:

- A Python-based ETL script for Open-Meteo API extraction and transformation.
- Cleaned weather datasets stored in CSV and a Microsoft SQL Server database.
- An interactive Dash dashboard with a few high-quality charts and planning indicators.
- A short analytical summary of observed weather patterns.
- A presentation or demonstration of the completed system.
