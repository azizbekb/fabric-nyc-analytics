CREATE   PROCEDURE dbo.load_dim_fx AS
BEGIN
    -- Only the days of DimDate, so every FX row has a date in the model.
    DELETE FROM dbo.DimFX;
    INSERT INTO dbo.DimFX (date_key, [date], usd_per_eur, is_filled)
    SELECT dd.date_key, fx.[date], fx.usd_per_eur, fx.is_filled
    FROM lh_silver.dbo.silver_fx_daily AS fx
    INNER JOIN dbo.DimDate AS dd ON dd.[date] = fx.[date];
END;

GO