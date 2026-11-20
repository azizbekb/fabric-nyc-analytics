CREATE TABLE [dbo].[DimFX] (
    [date_key]    INT             NOT NULL,
    [date]        DATE            NOT NULL,
    [usd_per_eur] DECIMAL (10, 6) NOT NULL,
    [is_filled]   BIT             NOT NULL
);


GO

ALTER TABLE [dbo].[DimFX]
    ADD CONSTRAINT [FK_DimFX_Date] FOREIGN KEY ([date_key]) REFERENCES [dbo].[DimDate] ([date_key]) NOT ENFORCED;


GO

ALTER TABLE [dbo].[DimFX]
    ADD CONSTRAINT [PK_DimFX] PRIMARY KEY NONCLUSTERED ([date_key] ASC) NOT ENFORCED;


GO