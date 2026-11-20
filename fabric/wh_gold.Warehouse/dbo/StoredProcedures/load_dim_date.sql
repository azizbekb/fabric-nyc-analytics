-- Gold load procedures for wh_gold. Each one fully reloads one table from lh_silver (DELETE + INSERT),
-- so a rerun always gives the same result. The pipeline calls them in the order of config gold.load_procedures.
-- DELETE, not TRUNCATE: Fabric Warehouse refuses TRUNCATE on a table referenced by a foreign key, even a NOT ENFORCED one.
-- Every column is alias-qualified (a documented requirement for Warehouse Git sync with cross-item references).

CREATE   PROCEDURE dbo.load_dim_date AS
BEGIN
    -- Calendar covering every fact day (taxi and air quality), without gaps.
    DECLARE @first date, @last date;
    SELECT @first = MIN(d.[date]), @last = MAX(d.[date])
    FROM (
        SELECT t.pickup_date AS [date] FROM lh_silver.dbo.silver_taxi_trips AS t
        UNION ALL
        SELECT a.[date] FROM lh_silver.dbo.silver_air_quality AS a
    ) AS d;

    DELETE FROM dbo.DimDate;
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