CREATE   PROCEDURE dbo.load_fact_taxi_daily AS
BEGIN
    -- Void pairs (charge + cancellation) are not trips. Outliers count as trips but are left out of averages.
    DELETE FROM dbo.FactTaxiDaily;
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