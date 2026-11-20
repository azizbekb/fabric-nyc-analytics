# Lineage

The flow as built. Item and table names come from `config/sources.json`. Everything runs in one
pipeline, `pl_daily` (daily at 06:00 Tashkent time, see [governance.md](governance.md#refresh-schedule)).

```mermaid
flowchart LR
  subgraph Sources
    TLC[NYC TLC Parquet]
    ZONES[Taxi zone CSV]
    MON[reference/monitor_zones.csv<br/>GitHub]
    OAQ[OpenAQ API v3]
    WB[World Bank API]
    ECB[ECB FX API]
  end

  subgraph Bronze[lh_bronze]
    B_TAXI[Files/taxi]
    B_ZONES[Files/taxi_zones]
    B_MON[Files/reference]
    B_OAQ[bronze_openaq_measurements]
    B_WB[bronze_worldbank_gdp]
    B_ECB[bronze_ecb_fx]
  end

  subgraph Silver[lh_silver]
    S_TAXI[silver_taxi_trips]
    Q_TAXI[quarantine_taxi_trips]
    S_ZONES[silver_taxi_zones]
    S_MON[silver_monitor_zones]
    S_AQ[silver_air_quality]
    Q_AQ[quarantine_air_quality]
    S_GDP[silver_gdp]
    Q_GDP[quarantine_gdp]
    S_FX[silver_fx_daily]
    Q_FX[quarantine_fx]
  end

  subgraph Gold[wh_gold]
    D_DATE[DimDate]
    D_ZONE[DimZone]
    D_LOC[DimLocation]
    D_FX[DimFX]
    D_GDP[DimGDP]
    F_TAXI[FactTaxiDaily]
    F_AQ[FactAirQualityDaily]
  end

  TLC -- Copy --> B_TAXI
  ZONES -- Copy --> B_ZONES
  MON -- Copy --> B_MON
  OAQ -- df_openaq --> B_OAQ
  WB -- df_worldbank --> B_WB
  ECB -- df_ecb --> B_ECB

  B_TAXI -- nb_silver --> S_TAXI & Q_TAXI
  B_ZONES -- nb_silver --> S_ZONES
  B_MON -- nb_silver --> S_MON
  B_OAQ -- nb_silver --> S_AQ & Q_AQ
  B_WB -- nb_silver --> S_GDP & Q_GDP
  B_ECB -- nb_silver --> S_FX & Q_FX

  S_TAXI & S_AQ --> D_DATE
  S_ZONES --> D_ZONE
  S_MON --> D_LOC
  S_FX --> D_FX
  S_GDP --> D_GDP
  S_TAXI & S_FX --> F_TAXI
  S_AQ --> F_AQ

  Gold --> SM[sm_nyc_analytics<br/>Direct Lake] --> RPT[rpt_nyc_analytics]
```

## Steps and the code behind them

| Step | Item | Code in the repo |
|---|---|---|
| Source → Bronze files | `pl_daily` Copy activities | `fabric/pl_daily.DataPipeline/pipeline-content.json` |
| Source → Bronze tables | Dataflows Gen2 `df_openaq`, `df_worldbank`, `df_ecb` | `fabric/df_*.Dataflow/mashup.pq` |
| Bronze → Silver | notebook `nb_silver`, rules in `nb_lib_*` | `fabric/nb_silver.Notebook/`, `fabric/nb_lib_*.Notebook/` |
| Silver → Gold | stored procedures `load_*` (order: `gold.load_procedures`) | `fabric/wh_gold.Warehouse/dbo/StoredProcedures/` |
| Gold → report | semantic model (Direct Lake), report | `fabric/sm_nyc_analytics.SemanticModel/`, `fabric/rpt_nyc_analytics.Report/` |

## Row reconciliation (2026-11-20, months 2024-01 … 2024-06)

| Check | Result |
|---|---|
| Bronze taxi rows = `silver_taxi_trips` + `quarantine_taxi_trips` | 20,237,796 + 94,297 (assert in `nb_silver`) |
| `SUM(FactTaxiDaily.trips)` = non-void rows in `silver_taxi_trips` | 19,791,824 = 19,791,824 |
| `FactAirQualityDaily` rows = `silver_air_quality` rows | 4,271 = 4,271 |
| Facts without a matching dimension row | 0 for every key |

Columns added on the way for tracing: `source_file` and `load_ts` (taxi, from Spark file metadata),
`source` and `load_ts` (API tables, from the dataflows), `reject_reason` (quarantine tables).
