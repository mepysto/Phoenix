"""FIRMS CSV parsing (no network, no database)."""

from datetime import UTC, datetime

from src.services.hazards.firms import parse_firms_csv

VIIRS = """latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,confidence,version,bright_ti5,frp,daynight
-8.5,120.6,330.1,0.4,0.4,2026-09-24,0142,N,high,2.0NRT,290.1,12.5,D
91.0,10.0,300,0.4,0.4,2026-09-24,0142,N,low,2.0NRT,290,1,N
10.0,10.0,300,0.4,0.4,bad-date,0142,N,low,2.0NRT,290,1,N
10.0,10.0,300,0.4,0.4,2026-09-24,42,N20,nominal,2.0NRT,290,,N
"""
MODIS = """latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,confidence,version,bright_t31,frp,daynight
1.49,127.63,310.2,1.0,1.0,2026-09-22,0011,T,66,6.1NRT,290.5,8.78,D
"""


def test_viirs_rows_parsed_and_invalid_rows_skipped() -> None:
    rows = list(parse_firms_csv(VIIRS))
    assert len(rows) == 2  # lat 91 and a bad date are dropped
    first, second = rows
    assert first.instrument == "VIIRS" and first.satellite == "N"
    assert first.acquired_at == datetime(2026, 9, 24, 1, 42, tzinfo=UTC)
    assert first.frp == 12.5 and first.brightness_k == 330.1 and first.confidence == "high"
    # acq_time "42" means 00:42; missing FRP stays None
    assert second.acquired_at == datetime(2026, 9, 24, 0, 42, tzinfo=UTC)
    assert second.frp is None and second.satellite == "N20"


def test_modis_columns_are_understood() -> None:
    (row,) = parse_firms_csv(MODIS)
    assert row.instrument == "MODIS"
    assert row.brightness_k == 310.2 and row.confidence == "66"
