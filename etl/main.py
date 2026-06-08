import logging
from datetime import datetime
import pandas as pd
import pyodbc
import openmeteo_requests
import requests_cache
from retry_requests import retry
# =========================================================
# 1. LOGGING CONFIGURATION
# =========================================================
# Logs are useful for monitoring pipeline progress, failures,
# record counts, and validation results.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# =========================================================
# 2. CONFIGURATION
# =========================================================
SERVER = "SERVER_NAME"
DATABASE = "WeatherPipelineDB"
DRIVER = "{ODBC Driver 17 for SQL Server}"

LOCATION_NAME = "Louisville"
LATITUDE = 38.2469
LONGITUDE = -85.7664
TIMEZONE = "America/New_York"

URL = "https://api.open-meteo.com/v1/forecast"

# Main weather variables selected from Open-Meteo hourly data
HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "cloud_cover",
    "precipitation_probability",
    "precipitation",
    "weather_code"
]

# =========================================================
# 3. DATABASE CONNECTION HELPERS
# =========================================================
def get_connection(database_name):
    conn_str = (
        f"DRIVER={DRIVER};"
        f"SERVER={SERVER};"
        f"DATABASE={database_name};"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)

def ensure_database_and_tables():
    """
    Connect to master, create target database if needed,
    then create required tables if they do not exist.
    """
    logging.info("Checking database and tables...")

    master_conn = get_connection("master")
    master_conn.autocommit = True
    master_cursor = master_conn.cursor()

    master_cursor.execute(f"""
    IF DB_ID('{DATABASE}') IS NULL
    BEGIN
        CREATE DATABASE {DATABASE};
    END
    """)
    master_cursor.close()
    master_conn.close()

    conn = get_connection(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
    IF OBJECT_ID('dbo.[user]', 'U') IS NULL
    CREATE TABLE dbo.[user] (
        user_id INT IDENTITY(1,1) PRIMARY KEY,
        first_name VARCHAR(50) NOT NULL,
        last_name VARCHAR(50) NOT NULL,
        email VARCHAR(255) NOT NULL UNIQUE,
        user_type VARCHAR(50) NOT NULL
    );
    """)

    cursor.execute("""
    IF OBJECT_ID('dbo.location', 'U') IS NULL
    CREATE TABLE dbo.location (
        location_id INT IDENTITY(1,1) PRIMARY KEY,
        user_id INT NOT NULL,
        location_name VARCHAR(100) NOT NULL,
        latitude DECIMAL(8,5) NOT NULL,
        longitude DECIMAL(8,5) NOT NULL,
        CONSTRAINT FK_location_user
            FOREIGN KEY (user_id) REFERENCES dbo.[user](user_id)
    );
    """)

    cursor.execute("""
    IF OBJECT_ID('dbo.weather_observation', 'U') IS NULL
    CREATE TABLE dbo.weather_observation (
        weather_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        location_id INT NOT NULL,
        forecast_timestamp DATETIME2 NOT NULL,
        temperature DECIMAL(5,2) NULL,
        humidity DECIMAL(5,2) NULL,
        wind_speed DECIMAL(5,2) NULL,
        cloud_cover DECIMAL(5,2) NULL,
        precipitation DECIMAL(5,2) NULL,
        rainfall_probability DECIMAL(5,2) NULL,
        weather_code INT NULL,
        CONSTRAINT FK_weather_location
            FOREIGN KEY (location_id) REFERENCES dbo.location(location_id),
        CONSTRAINT UQ_weather_location_timestamp
            UNIQUE (location_id, forecast_timestamp)
    );
    """)

    conn.commit()
    cursor.close()
    conn.close()
    logging.info("Database and tables are ready.")

# =========================================================
# 4. API EXTRACTION
# =========================================================
def extract_openmeteo_data():
    """
    Calls the Open-Meteo API and returns a DataFrame of hourly weather data.
    Includes retry and cache support.
    """
    logging.info("Starting API extraction from Open-Meteo...")

    cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": HOURLY_VARS,
        "timezone": TIMEZONE,
        "wind_speed_unit": "mph",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch"
    }

    responses = openmeteo.weather_api(URL, params=params)

    if not responses or len(responses) == 0:
        raise ValueError("API response is empty. No weather data returned.")

    response = responses[0]
    hourly = response.Hourly()

    hourly_data = {
        "forecast_timestamp": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ).tz_convert(response.Timezone().decode()),
        "temperature": hourly.Variables(0).ValuesAsNumpy(),
        "humidity": hourly.Variables(1).ValuesAsNumpy(),
        "wind_speed": hourly.Variables(2).ValuesAsNumpy(),
        "cloud_cover": hourly.Variables(3).ValuesAsNumpy(),
        "rainfall_probability": hourly.Variables(4).ValuesAsNumpy(),
        "precipitation": hourly.Variables(5).ValuesAsNumpy(),
        "weather_code": hourly.Variables(6).ValuesAsNumpy()
    }

    df = pd.DataFrame(hourly_data)
    logging.info(f"Extraction complete. Retrieved {len(df)} hourly records.")
    return df

# =========================================================
# 5. TRANSFORMATION & CLEANING
# =========================================================
def transform_and_clean(df):
    """
    Cleans and standardizes the extracted data.
    Also creates derived metrics to make the data analytics-ready.
    """
    logging.info("Starting data transformation and cleaning...")

    df = df.copy()

    # Convert timezone-aware datetime to naive datetime for SQL Server compatibility
    df["forecast_timestamp"] = pd.to_datetime(df["forecast_timestamp"]).dt.tz_localize(None)

    # Ensure numeric columns are properly typed
    numeric_cols = [
        "temperature", "humidity", "wind_speed",
        "cloud_cover", "precipitation",
        "rainfall_probability", "weather_code"
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Standardize weather_code as integer where possible
    df["weather_code"] = df["weather_code"].astype("Int64")

    # Derived metric: simple outdoor suitability flag
    def classify_outdoor_condition(row):
        if pd.isna(row["temperature"]) or pd.isna(row["rainfall_probability"]) or pd.isna(row["wind_speed"]):
            return "unknown"
        if row["rainfall_probability"] > 60 or row["wind_speed"] > 20:
            return "poor"
        elif row["rainfall_probability"] > 30 or row["temperature"] < 40 or row["temperature"] > 90:
            return "cautionary"
        else:
            return "favorable"

    df["outdoor_condition_flag"] = df.apply(classify_outdoor_condition, axis=1)

    # Drop exact duplicate rows from the extracted dataset
    before = len(df)
    df = df.drop_duplicates()
    after = len(df)

    logging.info(f"Transformation complete. Removed {before - after} duplicate rows during cleaning.")
    return df

# =========================================================
# 6. VALIDATION & DATA QUALITY CHECKS
# =========================================================
def validate_data(df):
    """
    Runs data quality checks and logs validation outcomes.
    Raises an exception for critical failures.
    """
    logging.info("Running data validation checks...")

    required_cols = [
        "forecast_timestamp", "temperature", "humidity",
        "wind_speed", "cloud_cover", "precipitation",
        "rainfall_probability", "weather_code"
    ]

    # Schema validation
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Schema validation failed. Missing columns: {missing_cols}")

    # Null checks
    null_counts = df[required_cols].isnull().sum()
    logging.info(f"Null value summary:\n{null_counts}")

    # Duplicate detection on business key
    dup_count = df.duplicated(subset=["forecast_timestamp"]).sum()
    if dup_count > 0:
        logging.warning(f"Duplicate forecast timestamps found in extracted dataset: {dup_count}")
    else:
        logging.info("No duplicate forecast timestamps found in extracted dataset.")

    # Range validation
    invalid_temp = df[(df["temperature"] < -100) | (df["temperature"] > 150)]
    invalid_humidity = df[(df["humidity"] < 0) | (df["humidity"] > 100)]
    invalid_cloud = df[(df["cloud_cover"] < 0) | (df["cloud_cover"] > 100)]
    invalid_rain_prob = df[(df["rainfall_probability"] < 0) | (df["rainfall_probability"] > 100)]
    invalid_precip = df[df["precipitation"] < 0]

    if len(invalid_temp) > 0:
        raise ValueError(f"Temperature range validation failed for {len(invalid_temp)} rows.")
    if len(invalid_humidity) > 0:
        raise ValueError(f"Humidity range validation failed for {len(invalid_humidity)} rows.")
    if len(invalid_cloud) > 0:
        raise ValueError(f"Cloud cover range validation failed for {len(invalid_cloud)} rows.")
    if len(invalid_rain_prob) > 0:
        raise ValueError(f"Rainfall probability validation failed for {len(invalid_rain_prob)} rows.")
    if len(invalid_precip) > 0:
        raise ValueError(f"Precipitation validation failed for {len(invalid_precip)} rows.")

    logging.info("All data validation checks passed.")

# =========================================================
# 7. ENSURE USER AND LOCATION EXIST
# =========================================================
def ensure_reference_data():
    """
    Ensures one user and one Louisville location exist before loading
    weather records. Returns location_id.
    """
    logging.info("Ensuring reference data exists in user and location tables...")

    conn = get_connection(DATABASE)
    cursor = conn.cursor()

    # Insert a default user only if it does not already exist
    cursor.execute("""
    IF NOT EXISTS (SELECT 1 FROM dbo.[user] WHERE email = ?)
    INSERT INTO dbo.[user] (first_name, last_name, email, user_type)
    VALUES (?, ?, ?, ?)
    """, ("ayo@example.com", "ayo", "wale", "ayo@example.com", "analyst"))

    conn.commit()

    # Get user_id
    cursor.execute("SELECT user_id FROM dbo.[user] WHERE email = ?", ("caleb@example.com",))
    user_id = cursor.fetchone()[0]

    # Insert Louisville location only if it does not already exist
    cursor.execute("""
    IF NOT EXISTS (
        SELECT 1 FROM dbo.location
        WHERE user_id = ? AND location_name = ? AND latitude = ? AND longitude = ?
    )
    INSERT INTO dbo.location (user_id, location_name, latitude, longitude)
    VALUES (?, ?, ?, ?)
    """, (user_id, LOCATION_NAME, LATITUDE, LONGITUDE, user_id, LOCATION_NAME, LATITUDE, LONGITUDE))

    conn.commit()

    # Get location_id
    cursor.execute("""
    SELECT location_id
    FROM dbo.location
    WHERE user_id = ? AND location_name = ? AND latitude = ? AND longitude = ?
    """, (user_id, LOCATION_NAME, LATITUDE, LONGITUDE))

    location_id = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    logging.info(f"Reference data ready. location_id = {location_id}")
    return location_id

# =========================================================
# 8. INCREMENTAL LOADING
# =========================================================
def load_weather_data_incrementally(df, location_id):
    """
    Incremental load strategy:
    - Prevent duplicate loads using unique key (location_id + forecast_timestamp)
    - Append only new records
    - Existing records are skipped
    """
    logging.info("Starting incremental load into weather_observation...")

    conn = get_connection(DATABASE)
    cursor = conn.cursor()

    insert_sql = """
    INSERT INTO dbo.weather_observation
    (location_id, forecast_timestamp, temperature, humidity, wind_speed,
     cloud_cover, precipitation, rainfall_probability, weather_code)
    SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?
    WHERE NOT EXISTS (
        SELECT 1
        FROM dbo.weather_observation
        WHERE location_id = ? AND forecast_timestamp = ?
    )
    """

    inserted_count = 0
    skipped_count = 0

    for _, row in df.iterrows():
        params = (
            location_id,
            row["forecast_timestamp"],
            row["temperature"],
            row["humidity"],
            row["wind_speed"],
            row["cloud_cover"],
            row["precipitation"],
            row["rainfall_probability"],
            int(row["weather_code"]) if pd.notna(row["weather_code"]) else None,
            location_id,
            row["forecast_timestamp"]
        )

        cursor.execute(insert_sql, params)

        if cursor.rowcount == 1:
            inserted_count += 1
        else:
            skipped_count += 1

    conn.commit()

    # Row count verification
    cursor.execute("SELECT COUNT(*) FROM dbo.weather_observation WHERE location_id = ?", (location_id,))
    total_rows = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    logging.info(f"Incremental load complete. Inserted: {inserted_count}, Skipped existing: {skipped_count}")
    logging.info(f"Total rows in weather_observation for location_id {location_id}: {total_rows}")

# =========================================================
# 9. MAIN PIPELINE EXECUTION
# =========================================================
def run_pipeline():
    """
    Main ETL flow:
    1. Create database/tables if needed
    2. Extract data from Open-Meteo
    3. Transform and clean
    4. Validate data quality
    5. Ensure reference tables exist
    6. Incrementally load weather data
    """
    try:
        logging.info("===== ETL PIPELINE STARTED =====")

        ensure_database_and_tables()

        raw_df = extract_openmeteo_data()
        clean_df = transform_and_clean(raw_df)
        validate_data(clean_df)

        location_id = ensure_reference_data()
        load_weather_data_incrementally(clean_df, location_id)

        logging.info("===== ETL PIPELINE COMPLETED SUCCESSFULLY =====")

    except Exception as e:
        logging.exception(f"ETL pipeline failed: {e}")
        raise

# =========================================================
# 10. RUN SCRIPT
# =========================================================
if __name__ == "__main__":
    run_pipeline()