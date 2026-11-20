CREATE TABLE [dbo].[DimLocation] (
    [location_id]   INT           NOT NULL,
    [location_name] VARCHAR (100) NULL,
    [latitude]      FLOAT (53)    NULL,
    [longitude]     FLOAT (53)    NULL,
    [zone_id]       INT           NULL,
    [zone]          VARCHAR (100) NULL,
    [borough]       VARCHAR (20)  NULL
);


GO

ALTER TABLE [dbo].[DimLocation]
    ADD CONSTRAINT [PK_DimLocation] PRIMARY KEY NONCLUSTERED ([location_id] ASC) NOT ENFORCED;


GO