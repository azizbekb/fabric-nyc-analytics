CREATE TABLE [dbo].[DimZone] (
    [zone_id]      INT           NOT NULL,
    [borough]      VARCHAR (20)  NULL,
    [zone]         VARCHAR (100) NULL,
    [service_zone] VARCHAR (20)  NULL
);


GO

ALTER TABLE [dbo].[DimZone]
    ADD CONSTRAINT [PK_DimZone] PRIMARY KEY NONCLUSTERED ([zone_id] ASC) NOT ENFORCED;


GO