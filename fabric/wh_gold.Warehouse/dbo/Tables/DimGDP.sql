CREATE TABLE [dbo].[DimGDP] (
    [year]         SMALLINT        NOT NULL,
    [country_code] VARCHAR (3)     NOT NULL,
    [gdp_usd]      DECIMAL (20, 2) NOT NULL
);


GO

ALTER TABLE [dbo].[DimGDP]
    ADD CONSTRAINT [PK_DimGDP] PRIMARY KEY NONCLUSTERED ([year] ASC) NOT ENFORCED;


GO