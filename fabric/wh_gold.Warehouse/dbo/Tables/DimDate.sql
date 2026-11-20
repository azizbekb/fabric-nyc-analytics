CREATE TABLE [dbo].[DimDate] (
    [date_key]    INT          NOT NULL,
    [date]        DATE         NOT NULL,
    [year]        SMALLINT     NOT NULL,
    [quarter]     SMALLINT     NOT NULL,
    [month]       SMALLINT     NOT NULL,
    [month_name]  VARCHAR (10) NOT NULL,
    [day]         SMALLINT     NOT NULL,
    [day_of_week] SMALLINT     NOT NULL,
    [day_name]    VARCHAR (10) NOT NULL,
    [is_weekend]  BIT          NOT NULL
);


GO

ALTER TABLE [dbo].[DimDate]
    ADD CONSTRAINT [PK_DimDate] PRIMARY KEY NONCLUSTERED ([date_key] ASC) NOT ENFORCED;


GO