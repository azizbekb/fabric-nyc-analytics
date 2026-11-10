-- Gold load procedures for wh_gold. Each one fully reloads one table from lh_silver (TRUNCATE + INSERT),
-- so a rerun always gives the same result. The pipeline calls them in the order of config gold.load_procedures.
-- Every column is alias-qualified (a documented requirement for Warehouse Git sync with cross-item references).

CREATE PROCEDURE dbo.load_dim_date AS
BEGIN
    -- Calendar covering every fact day (taxi and air quality), without gaps.
    DECLARE @first date, @last date;
    SELECT @first = MIN(d.[date]), @last = MAX(d.[date])
    FROM (
        SELECT t.pickup_date AS [date] FROM lh_silver.dbo.silver_taxi_trips AS t
        UNION ALL
        SELECT a.[date] FROM lh_silver.dbo.silver_air_quality AS a
    ) AS d;

    TRUNCATE TABLE dbo.DimDate;
    INSERT INTO dbo.DimDate (date_key, [date], [year], [quarter], [month], month_name, [day], day_of_week, day_name, is_weekend)
    SELECT
        YEAR(c.d) * 10000 + MONTH(c.d) * 100 + DAY(c.d),
        c.d,
        YEAR(c.d),
        DATEPART(quarter, c.d),
        MONTH(c.d),
        DATENAME(month, c.d),
        DAY(c.d),
        c.dow,
        DATENAME(weekday, c.d),
        CASE WHEN c.dow >= 6 THEN 1 ELSE 0 END
    FROM (
        SELECT
            DATEADD(day, s.value, @first) AS d,
            DATEDIFF(day, '19000101', DATEADD(day, s.value, @first)) % 7 + 1 AS dow  -- 1900-01-01 was a Monday
        FROM GENERATE_SERIES(0, DATEDIFF(day, @first, @last)) AS s
    ) AS c;
END;
GO

CREATE PROCEDURE dbo.load_dim_zone AS
BEGIN
    TRUNCATE TABLE dbo.DimZone;
    INSERT INTO dbo.DimZone (zone_id, borough, zone, service_zone)
    SELECT z.location_id, z.borough, z.zone, z.service_zone
    FROM lh_silver.dbo.silver_taxi_zones AS z;
END;
GO

CREATE PROCEDURE dbo.load_dim_location AS
BEGIN
    TRUNCATE TABLE dbo.DimLocation;
    INSERT INTO dbo.DimLocation (location_id, location_name, latitude, longitude, zone_id, zone, borough)
    SELECT m.location_id, m.location_name, m.latitude, m.longitude, m.zone_id, m.zone, m.borough
    FROM lh_silver.dbo.silver_monitor_zones AS m;
END;
GO

CREATE PROCEDURE dbo.load_dim_fx AS
BEGIN
    -- Only the days of DimDate, so every FX row has a date in the model.
    TRUNCATE TABLE dbo.DimFX;
    INSERT INTO dbo.DimFX (date_key, [date], usd_per_eur, is_filled)
    SELECT dd.date_key, fx.[date], fx.usd_per_eur, fx.is_filled
    FROM lh_silver.dbo.silver_fx_daily AS fx
    INNER JOIN dbo.DimDate AS dd ON dd.[date] = fx.[date];
END;
GO

CREATE PROCEDURE dbo.load_dim_gdp AS
BEGIN
    TRUNCATE TABLE dbo.DimGDP;
    INSERT INTO dbo.DimGDP ([year], country_code, gdp_usd)
    SELECT g.[year], g.country_code, g.gdp_usd
    FROM lh_silver.dbo.silver_gdp AS g;
END;
GO

CREATE PROCEDURE dbo.load_fact_taxi_daily AS
BEGIN
    -- Void pairs (charge + cancellation) are not trips. Outliers count as trips but are left out of averages.
    TRUNCATE TABLE dbo.FactTaxiDaily;
    INSERT INTO dbo.FactTaxiDaily (date_key, zone_id, trips, clean_trips, total_fare_usd, total_amount_usd,
                                   total_amount_eur, avg_fare_usd, avg_distance_mi, avg_duration_min)
    SELECT
        YEAR(d.pickup_date) * 10000 + MONTH(d.pickup_date) * 100 + DAY(d.pickup_date),
        d.zone_id, d.trips, d.clean_trips, d.total_fare_usd, d.total_amount_usd,
        CAST(d.total_amount_usd / fx.usd_per_eur AS decimal(18, 2)),
        d.avg_fare_usd, d.avg_distance_mi, d.avg_duration_min
    FROM (
        SELECT
            t.pickup_date,
            t.pu_location_id AS zone_id,
            COUNT(*) AS trips,
            SUM(CASE WHEN t.is_outlier = 0 THEN 1 ELSE 0 END) AS clean_trips,
            CAST(SUM(t.fare_amount) AS decimal(18, 2)) AS total_fare_usd,
            CAST(SUM(t.total_amount) AS decimal(18, 2)) AS total_amount_usd,
            CAST(AVG(CASE WHEN t.is_outlier = 0 THEN t.fare_amount END) AS decimal(10, 2)) AS avg_fare_usd,
            CAST(AVG(CASE WHEN t.is_outlier = 0 THEN t.trip_distance END) AS decimal(10, 2)) AS avg_distance_mi,
            CAST(AVG(CASE WHEN t.is_outlier = 0 THEN t.trip_duration_min END) AS decimal(10, 2)) AS avg_duration_min
        FROM lh_silver.dbo.silver_taxi_trips AS t
        WHERE t.is_void = 0
        GROUP BY t.pickup_date, t.pu_location_id
    ) AS d
    LEFT JOIN lh_silver.dbo.silver_fx_daily AS fx ON fx.[date] = d.pickup_date;
END;
GO

CREATE PROCEDURE dbo.load_fact_air_quality_daily AS
BEGIN
    TRUNCATE TABLE dbo.FactAirQualityDaily;
    INSERT INTO dbo.FactAirQualityDaily (date_key, location_id, parameter, units, avg_value, min_value, max_value, is_low_coverage)
    SELECT
        YEAR(a.[date]) * 10000 + MONTH(a.[date]) * 100 + DAY(a.[date]),
        a.location_id,
        a.parameter,
        MAX(a.units),
        AVG(a.value),
        MIN(a.value_min),
        MAX(a.value_max),
        MAX(CASE WHEN a.is_low_coverage = 1 THEN 1 ELSE 0 END)
    FROM lh_silver.dbo.silver_air_quality AS a
    GROUP BY a.[date], a.location_id, a.parameter;
END;
GO
