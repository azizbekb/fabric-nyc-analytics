CREATE   PROCEDURE dbo.load_dim_location AS
BEGIN
    DELETE FROM dbo.DimLocation;
    INSERT INTO dbo.DimLocation (location_id, location_name, latitude, longitude, zone_id, zone, borough)
    SELECT m.location_id, m.location_name, m.latitude, m.longitude, m.zone_id, m.zone, m.borough
    FROM lh_silver.dbo.silver_monitor_zones AS m;
END;

GO