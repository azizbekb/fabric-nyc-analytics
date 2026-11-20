CREATE TABLE [dbo].[FactAirQualityDaily] (
    [date_key]        INT          NOT NULL,
    [location_id]     INT          NOT NULL,
    [parameter]       VARCHAR (10) NOT NULL,
    [units]           VARCHAR (10) NULL,
    [avg_value]       FLOAT (53)   NULL,
    [min_value]       FLOAT (53)   NULL,
    [max_value]       FLOAT (53)   NULL,
    [is_low_coverage] BIT          NOT NULL
);


GO

ALTER TABLE [dbo].[FactAirQualityDaily]
    ADD CONSTRAINT [FK_FactAirQualityDaily_Date] FOREIGN KEY ([date_key]) REFERENCES [dbo].[DimDate] ([date_key]) NOT ENFORCED;


GO

ALTER TABLE [dbo].[FactAirQualityDaily]
    ADD CONSTRAINT [FK_FactAirQualityDaily_Loc] FOREIGN KEY ([location_id]) REFERENCES [dbo].[DimLocation] ([location_id]) NOT ENFORCED;


GO