CREATE   PROCEDURE dbo.load_dim_zone AS
BEGIN
    DELETE FROM dbo.DimZone;
    INSERT INTO dbo.DimZone (zone_id, borough, zone, service_zone)
    SELECT z.location_id, z.borough, z.zone, z.service_zone
    FROM lh_silver.dbo.silver_taxi_zones AS z;
END;

GO