CREATE   PROCEDURE dbo.load_dim_gdp AS
BEGIN
    DELETE FROM dbo.DimGDP;
    INSERT INTO dbo.DimGDP ([year], country_code, gdp_usd)
    SELECT g.[year], g.country_code, g.gdp_usd
    FROM lh_silver.dbo.silver_gdp AS g;
END;

GO