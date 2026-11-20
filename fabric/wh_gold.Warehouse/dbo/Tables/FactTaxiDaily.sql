CREATE TABLE [dbo].[FactTaxiDaily] (
    [date_key]         INT             NOT NULL,
    [zone_id]          INT             NOT NULL,
    [trips]            INT             NOT NULL,
    [clean_trips]      INT             NOT NULL,
    [total_fare_usd]   DECIMAL (18, 2) NOT NULL,
    [total_amount_usd] DECIMAL (18, 2) NOT NULL,
    [total_amount_eur] DECIMAL (18, 2) NULL,
    [avg_fare_usd]     DECIMAL (10, 2) NULL,
    [avg_distance_mi]  DECIMAL (10, 2) NULL,
    [avg_duration_min] DECIMAL (10, 2) NULL
);


GO

ALTER TABLE [dbo].[FactTaxiDaily]
    ADD CONSTRAINT [FK_FactTaxiDaily_Date] FOREIGN KEY ([date_key]) REFERENCES [dbo].[DimDate] ([date_key]) NOT ENFORCED;


GO

ALTER TABLE [dbo].[FactTaxiDaily]
    ADD CONSTRAINT [FK_FactTaxiDaily_Zone] FOREIGN KEY ([zone_id]) REFERENCES [dbo].[DimZone] ([zone_id]) NOT ENFORCED;


GO