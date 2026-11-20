CREATE   PROCEDURE dbo.load_fact_air_quality_daily AS
BEGIN
    DELETE FROM dbo.FactAirQualityDaily;
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