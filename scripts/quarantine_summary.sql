-- Quarantine and quality-flag summary. Run on the lh_silver SQL analytics endpoint.
SELECT 'taxi' AS src, reject_reason, COUNT(*) AS n FROM dbo.quarantine_taxi_trips GROUP BY reject_reason
UNION ALL SELECT 'air', reject_reason, COUNT(*) FROM dbo.quarantine_air_quality GROUP BY reject_reason
UNION ALL SELECT 'gdp', reject_reason, COUNT(*) FROM dbo.quarantine_gdp GROUP BY reject_reason
UNION ALL SELECT 'fx', reject_reason, COUNT(*) FROM dbo.quarantine_fx GROUP BY reject_reason
UNION ALL SELECT 'flag', 'is_void', SUM(CAST(is_void AS int)) FROM dbo.silver_taxi_trips
UNION ALL SELECT 'flag', 'is_outlier', SUM(CAST(is_outlier AS int)) FROM dbo.silver_taxi_trips
UNION ALL SELECT 'flag', 'is_passenger_count_missing', SUM(CAST(is_passenger_count_missing AS int)) FROM dbo.silver_taxi_trips
UNION ALL SELECT 'flag', 'is_low_coverage', SUM(CAST(is_low_coverage AS int)) FROM dbo.silver_air_quality
ORDER BY src, n DESC;
