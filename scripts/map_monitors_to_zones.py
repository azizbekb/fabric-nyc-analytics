"""Map the configured OpenAQ monitors to TLC taxi zones (point-in-polygon) -> reference/monitor_zones.csv.

Run locally, once, and again when monitors or parameters change:
    python scripts/map_monitors_to_zones.py
Needs OPENAQ_API_KEY in .env and geopandas (local only; Fabric just reads the CSV).
"""
import json
import os

import geopandas as gpd
import pandas as pd
import requests
from dotenv import load_dotenv

CFG = json.load(open("config/sources.json"))


def fetch_monitors(oa, api_key):
    params = {"coordinates": f"{oa['center']['lat']},{oa['center']['lon']}", "radius": oa["radius_m"], "limit": oa["page_limit"]}
    rows, page = [], 1
    while True:
        r = requests.get(f"{oa['base_url']}/{oa['locations_path']}", headers={"X-API-Key": api_key}, params={**params, "page": page}, timeout=60)
        r.raise_for_status()
        batch = r.json()["results"]
        rows += batch
        if len(batch) < oa["page_limit"]:
            return [loc for loc in rows if is_selected(loc, oa)]
        page += 1


def is_selected(loc, oa):
    has_parameter = any(s["parameter"]["name"] in oa["parameters"] for s in loc["sensors"])
    return has_parameter and (loc["isMonitor"] or not oa["monitors_only"])


def to_points(monitors):
    df = pd.DataFrame({
        "location_id": [m["id"] for m in monitors],
        "location_name": [m["name"] for m in monitors],
        "latitude": [m["coordinates"]["latitude"] for m in monitors],
        "longitude": [m["coordinates"]["longitude"] for m in monitors],
    })
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude), crs="EPSG:4326")


def map_to_zones(points, zones, outside_label):
    joined = gpd.sjoin(points.to_crs(zones.crs), zones[["LocationID", "zone", "borough", "geometry"]], how="left", predicate="within")
    out = joined.drop(columns=["geometry", "index_right"]).rename(columns={"LocationID": "zone_id"})
    out["zone_id"] = out["zone_id"].astype("Int64")
    out["borough"] = out["borough"].fillna(outside_label)
    return out.drop_duplicates("location_id").sort_values("location_id")


def main():
    load_dotenv(".env")
    tz, mz = CFG["taxi_zones"], CFG["monitor_zones"]
    zones = gpd.read_file(f"/vsizip/vsicurl/{tz['base_url']}/{tz['shapefile_path']}/{tz['shapefile_member']}")
    monitors = fetch_monitors(CFG["openaq"], os.environ["OPENAQ_API_KEY"])
    result = map_to_zones(to_points(monitors), zones, mz["outside_label"])
    os.makedirs(os.path.dirname(mz["path"]), exist_ok=True)
    result.to_csv(mz["path"], index=False)
    print(f"{len(result)} monitors -> {mz['path']}")


if __name__ == "__main__":
    main()
