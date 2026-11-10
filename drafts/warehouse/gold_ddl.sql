-- Gold star schema for wh_gold (Fabric Warehouse).
-- Draft: after Git is connected these objects live in the wh_gold.Warehouse database project; then this file is deleted.
-- Fabric rules used: no nvarchar/datetime/tinyint (varchar, date, smallint); keys are added with ALTER TABLE
-- and must be NONCLUSTERED NOT ENFORCED; no default constraints.

CREATE TABLE dbo.DimDate (
    date_key     int         NOT NULL,  -- yyyymmdd
    [date]       date        NOT NULL,
    [year]       smallint    NOT NULL,
    [quarter]    smallint    NOT NULL,
    [month]      smallint    NOT NULL,
    month_name   varchar(10) NOT NULL,
    [day]        smallint    NOT NULL,
    day_of_week  smallint    NOT NULL,  -- 1 = Monday ... 7 = Sunday
    day_name     varchar(10) NOT NULL,
    is_weekend   bit         NOT NULL
);

CREATE TABLE dbo.DimZone (
    zone_id      int          NOT NULL,  -- TLC LocationID
    borough      varchar(20)  NULL,
    zone         varchar(100) NULL,
    service_zone varchar(20)  NULL
);

CREATE TABLE dbo.DimLocation (
    location_id   int          NOT NULL,  -- OpenAQ location id
    location_name varchar(100) NULL,
    latitude      float        NULL,
    longitude     float        NULL,
    zone_id       int          NULL,      -- NULL outside NYC
    zone          varchar(100) NULL,
    borough       varchar(20)  NULL       -- 'Outside NYC' for New Jersey monitors
);

CREATE TABLE dbo.DimFX (
    date_key    int            NOT NULL,
    [date]      date           NOT NULL,
    usd_per_eur decimal(10, 6) NOT NULL,  -- USD for 1 EUR
    is_filled   bit            NOT NULL   -- weekend/holiday: last available rate
);

CREATE TABLE dbo.DimGDP (
    [year]       smallint     NOT NULL,
    country_code varchar(3)   NOT NULL,
    gdp_usd      decimal(20, 2) NOT NULL  -- current USD
);

CREATE TABLE dbo.FactTaxiDaily (
    date_key         int            NOT NULL,
    zone_id          int            NOT NULL,  -- pickup zone
    trips            int            NOT NULL,  -- void pairs excluded
    clean_trips      int            NOT NULL,  -- trips without is_outlier; base of the averages
    total_fare_usd   decimal(18, 2) NOT NULL,
    total_amount_usd decimal(18, 2) NOT NULL,
    total_amount_eur decimal(18, 2) NULL,      -- total_amount_usd / usd_per_eur of that day
    avg_fare_usd     decimal(10, 2) NULL,
    avg_distance_mi  decimal(10, 2) NULL,
    avg_duration_min decimal(10, 2) NULL
);

CREATE TABLE dbo.FactAirQualityDaily (
    date_key        int         NOT NULL,
    location_id     int         NOT NULL,
    parameter       varchar(10) NOT NULL,  -- pm25, no2, o3
    units           varchar(10) NULL,
    avg_value       float       NULL,
    min_value       float       NULL,
    max_value       float       NULL,
    is_low_coverage bit         NOT NULL
);

ALTER TABLE dbo.DimDate     ADD CONSTRAINT PK_DimDate     PRIMARY KEY NONCLUSTERED (date_key) NOT ENFORCED;
ALTER TABLE dbo.DimZone     ADD CONSTRAINT PK_DimZone     PRIMARY KEY NONCLUSTERED (zone_id) NOT ENFORCED;
ALTER TABLE dbo.DimLocation ADD CONSTRAINT PK_DimLocation PRIMARY KEY NONCLUSTERED (location_id) NOT ENFORCED;
ALTER TABLE dbo.DimFX       ADD CONSTRAINT PK_DimFX       PRIMARY KEY NONCLUSTERED (date_key) NOT ENFORCED;
ALTER TABLE dbo.DimGDP      ADD CONSTRAINT PK_DimGDP      PRIMARY KEY NONCLUSTERED ([year]) NOT ENFORCED;

ALTER TABLE dbo.FactTaxiDaily       ADD CONSTRAINT FK_FactTaxiDaily_Date       FOREIGN KEY (date_key)    REFERENCES dbo.DimDate (date_key) NOT ENFORCED;
ALTER TABLE dbo.FactTaxiDaily       ADD CONSTRAINT FK_FactTaxiDaily_Zone       FOREIGN KEY (zone_id)     REFERENCES dbo.DimZone (zone_id) NOT ENFORCED;
ALTER TABLE dbo.FactAirQualityDaily ADD CONSTRAINT FK_FactAirQualityDaily_Date FOREIGN KEY (date_key)    REFERENCES dbo.DimDate (date_key) NOT ENFORCED;
ALTER TABLE dbo.FactAirQualityDaily ADD CONSTRAINT FK_FactAirQualityDaily_Loc  FOREIGN KEY (location_id) REFERENCES dbo.DimLocation (location_id) NOT ENFORCED;
ALTER TABLE dbo.DimFX               ADD CONSTRAINT FK_DimFX_Date               FOREIGN KEY (date_key)    REFERENCES dbo.DimDate (date_key) NOT ENFORCED;
