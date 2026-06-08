import pandas as pd
import pyodbc

# ----------------------------
# Connection settings
# ----------------------------
server = "SERVER_NAME"
database = "WeatherPipelineDB"
driver = "{ODBC Driver 17 for SQL Server}"

import pandas as pd
import pyodbc

# ----------------------------
# Connection settings
# ---------------------------
server = "SERVER_NAME"
driver = "{ODBC Driver 17 for SQL Server}"
database = "WeatherPipelineDB"

# ----------------------------
# Step 1: Connect to master and create database 
# --------------------------------------------------
# We connect to master first because WeatherPipelineDB does not exist yet.
# This allows us to create the database safely.
master_conn_str = (
    f"DRIVER={driver};"
    f"SERVER={server};"
    "DATABASE=master;"
    "Trusted_Connection=yes;"
)

master_conn = pyodbc.connect(master_conn_str)
master_conn.autocommit = True
master_cursor = master_conn.cursor()

# --------------------------------------------------
# Create the target database "WeatherPipelineDB"
# --------------------------------------------------
# DB_ID returns NULL if the database does not exist.
# If the database is missing, create it.
master_cursor.execute(f"""
IF DB_ID('{database}') IS NULL
BEGIN
    CREATE DATABASE {database};
END
""")
# Close the master connection after the database is created.
master_cursor.close()
master_conn.close()

# ----------------------------
# Step 2: Connect to the target database
# --------------------------------------------------
# Now that the database exists, connect directly to it.
conn_str = (
    f"DRIVER={driver};"
    f"SERVER={server};"
    f"DATABASE={database};"
    "Trusted_Connection=yes;"
)

conn = pyodbc.connect(conn_str)
conn.autocommit = False
cursor = conn.cursor()

# --------------------------------------------------
# Step 3: Drop tables if they already exist
# --------------------------------------------------
# Dropping in reverse dependency order avoids foreign key conflicts:
# weather_observation depends on location, and location depends on user.
cursor.execute("""
IF OBJECT_ID('dbo.weather_observation', 'U') IS NOT NULL DROP TABLE dbo.weather_observation;
IF OBJECT_ID('dbo.location', 'U') IS NOT NULL DROP TABLE dbo.location;
IF OBJECT_ID('dbo.[user]', 'U') IS NOT NULL DROP TABLE dbo.[user];
""")
conn.commit()

# --------------------------------------------------
# Step 4: Create the user table
# --------------------------------------------------
# Stores dashboard users or project users.
# user_id is the primary key.
cursor.execute("""
CREATE TABLE dbo.[user] (
    user_id INT IDENTITY(1,1) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(255) NOT NULL,
    user_type VARCHAR(50) NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT PK_user PRIMARY KEY (user_id),
    CONSTRAINT UQ_user_email UNIQUE (email)
);
""")

# --------------------------------------------------
# Step 5: Create the location table
# --------------------------------------------------
# Stores selected locations and geographic coordinates.
# user_id is a foreign key pointing to user.user_id.
cursor.execute("""
CREATE TABLE dbo.location (
    location_id INT IDENTITY(1,1) NOT NULL,
    user_id INT NOT NULL,
    location_name VARCHAR(100) NOT NULL,
    latitude DECIMAL(8,5) NOT NULL,
    longitude DECIMAL(8,5) NOT NULL,
    timezone VARCHAR(100) NULL,
    is_default BIT NOT NULL DEFAULT 0,
    created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT PK_location PRIMARY KEY (location_id),
    CONSTRAINT FK_location_user
        FOREIGN KEY (user_id) REFERENCES dbo.[user](user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
""")

# --------------------------------------------------
# Step 6: Create the weather_observation table
# --------------------------------------------------
# Stores the actual weather forecast records from Open-Meteo.
# location_id is a foreign key pointing to location.location_id.
cursor.execute("""
CREATE TABLE dbo.weather_observation (
    weather_id BIGINT IDENTITY(1,1) NOT NULL,
    location_id INT NOT NULL,
    forecast_timestamp DATETIME2 NOT NULL,
    temperature DECIMAL(5,2) NULL,
    humidity DECIMAL(5,2) NULL,
    wind_speed DECIMAL(5,2) NULL,
    cloud_cover DECIMAL(5,2) NULL,
    precipitation DECIMAL(5,2) NULL,
    rainfall_probability DECIMAL(5,2) NULL,
    weather_code INT NULL,
    CONSTRAINT PK_weather_observation PRIMARY KEY (weather_id),
    CONSTRAINT FK_weather_location
        FOREIGN KEY (location_id) REFERENCES dbo.location(location_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
""")
# Save the table creation changes.
conn.commit()

