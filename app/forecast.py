from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional, Set
from fastapi import HTTPException

FIELD_MAP = {
    "temperature": ("temperature_2m", "temperature"),
    "humidity": ("relative_humidity_2m", "humidity"),
    "wind_speed": ("wind_speed_10m", "wind_speed"),
    "precipitation": ("precipitation", "precipitation"),
}

def normalize_time_to_today_iso(time_str: str) -> str:
    t = (time_str or "").strip()
    if not t:
        raise HTTPException(400, "time is empty")

    if "T" in t:
        try:
            dt = datetime.fromisoformat(t)
        except ValueError:
            raise HTTPException(400, "Invalid ISO time. Use YYYY-MM-DDTHH:MM")
        return dt.strftime("%Y-%m-%dT%H:%M")

    parts = t.split(":")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        raise HTTPException(400, "time must be HH:MM or ISO YYYY-MM-DDTHH:MM")
    hh, mm = int(parts[0]), int(parts[1])
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        raise HTTPException(400, "time out of range")
    return f"{date.today().isoformat()}T{hh:02d}:{mm:02d}"

def parse_fields(fields: Optional[str]) -> Set[str]:
    if fields is None or not fields.strip():
        return set(FIELD_MAP.keys())
    items = {x.strip() for x in fields.split(",") if x.strip()}
    if not items:
        raise HTTPException(400, "fields is empty")
    unknown = [f for f in items if f not in FIELD_MAP]
    if unknown:
        raise HTTPException(400, f"Unknown field(s): {', '.join(unknown)}")
    return items

def pick_at_time(hourly: Dict[str, Any], iso_time: str, fields_set: Set[str]) -> Dict[str, Any]:
    times = hourly.get("time")
    if not isinstance(times, list) or not times:
        raise HTTPException(500, "Stored forecast missing hourly.time")

    try:
        idx = times.index(iso_time)
    except ValueError:
        raise HTTPException(404, f"No hourly data for time={iso_time}")

    out: Dict[str, Any] = {"time": iso_time}
    for f in fields_set:
        src_key, out_key = FIELD_MAP[f]
        arr = hourly.get(src_key)
        if not isinstance(arr, list) or idx >= len(arr):
            raise HTTPException(500, f"Stored forecast missing hourly.{src_key}")
        out[out_key] = arr[idx]
    return out