"""Infrastructure dataset parsing (no network, no database)."""

import math

from scripts.import_infrastructure import parse_dams, parse_power_plants


def test_power_plant_fields_and_invalid_rows_skipped() -> None:
    rows = [
        {"gppd_idnr": "A", "name": "Three Gorges Dam", "country_long": "China", "capacity_mw": "22500",
         "latitude": "30.82", "longitude": "111.0", "primary_fuel": "Hydro", "commissioning_year": "2003.0",
         "owner": ""},
        {"gppd_idnr": "B", "name": "nowhere", "latitude": "0", "longitude": "0", "capacity_mw": "5"},
        {"gppd_idnr": "C", "name": "bad lat", "latitude": "123", "longitude": "10", "capacity_mw": "5"},
        {"gppd_idnr": "", "name": "no id", "latitude": "10", "longitude": "10", "capacity_mw": "5"},
    ]
    (asset,) = list(parse_power_plants(rows))
    assert asset["source_id"] == "A" and asset["kind"] == "power_plant"
    assert asset["importance"] == 22500
    assert asset["attributes"]["commissioning_year"] == 2003
    assert asset["attributes"]["owner"] is None  # '' -> None


def test_dam_sentinels_become_null_and_name_falls_back_to_reservoir() -> None:
    records = [
        {"GDW_ID": 7.0, "DAM_NAME": math.nan, "RES_NAME": "Lake X", "DAM_HGT_M": -99,
         "YEAR_DAM": -99, "CAP_MCM": 120.5, "COUNTRY": "Chile", "lng": -70.1, "lat": -33.4},
        {"GDW_ID": 8, "DAM_NAME": "No location", "lng": None, "lat": None},
    ]
    (dam,) = list(parse_dams(records))
    assert dam["source_id"] == "7"
    assert dam["name"] == "Lake X"
    assert dam["importance"] is None
    assert dam["attributes"]["height_m"] is None and dam["attributes"]["year"] is None
    assert dam["attributes"]["capacity_mcm"] == 120.5
