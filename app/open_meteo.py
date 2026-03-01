from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

import httpx
from app.config import OPEN_METEO_URL, GEOCODING_URL, HTTP_TIMEOUT_SECONDS


async def _get_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        r = await client.get(url, params=params)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
        return r.json()


async def get_current_weather(lat: float, lon: float) -> Dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,wind_speed_10m,surface_pressure",
        "timezone": "auto",
    }
    data = await _get_json(OPEN_METEO_URL, params)
    cur = data.get("current")
    if not isinstance(cur, dict):
        raise RuntimeError("Open-Meteo: missing current")
    return {
        "time": cur.get("time"),
        "temperature": cur.get("temperature_2m"),
        "wind_speed": cur.get("wind_speed_10m"),
        "pressure": cur.get("surface_pressure"),
    }


async def fetch_today_hourly(lat: float, lon: float) -> Dict[str, Any]:
    today = date.today().isoformat()
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
        "start_date": today,
        "end_date": today,
        "timezone": "auto",
    }
    data = await _get_json(OPEN_METEO_URL, params)
    hourly = data.get("hourly")
    if not isinstance(hourly, dict):
        raise RuntimeError("Open-Meteo: missing hourly")
    return hourly


async def search_cities(query: str, count: int = 10, language: str = "ru") -> List[Dict[str, Any]]:
    params = {
        "name": query,
        "count": count,
        "language": language,
        "format": "json",
    }
    data = await _get_json(GEOCODING_URL, params)
    results = data.get("results") or []
    out: List[Dict[str, Any]] = []
    for item in results:
        out.append({
            "name": item.get("name"),
            "country": item.get("country"),
            "admin1": item.get("admin1"),
            "latitude": item.get("latitude"),
            "longitude": item.get("longitude"),
            "timezone": item.get("timezone"),
            "population": item.get("population"),
        })
    return out