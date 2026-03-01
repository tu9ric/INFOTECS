from __future__ import annotations

import json
from datetime import datetime, date, timezone
from typing import Any, Optional, Tuple

import aiosqlite
from app.config import DB_PATH, UPDATE_INTERVAL_SECONDS

def utcnow_iso() -> str:
    return datetime.utcnow().isoformat()

def parse_iso(ts: str) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def is_stale(updated_at: Optional[str]) -> bool:
    if not updated_at:
        return True
    dt = parse_iso(updated_at)
    if not dt:
        return True
    age = (datetime.now(timezone.utc) - dt).total_seconds()
    return age >= UPDATE_INTERVAL_SECONDS

async def insert_city(name: str, lat: float, lon: float) -> int:
    now = utcnow_iso()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO cities(name, lat, lon, created_at) VALUES(?,?,?,?)",
            (name, lat, lon, now),
        )
        await db.commit()
        return cur.lastrowid

async def list_cities() -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT name, lat, lon FROM cities ORDER BY name")
        rows = await cur.fetchall()
    return [{"name": n, "lat": la, "lon": lo} for (n, la, lo) in rows]

async def list_city_rows_with_today_updated() -> list[Tuple[int, float, float, Optional[str]]]:
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT c.id, c.lat, c.lon, f.updated_at
            FROM cities c
            LEFT JOIN forecasts f
              ON f.city_id = c.id AND f.forecast_date = ?
            """,
            (today,),
        )
        return await cur.fetchall()

async def get_city_id(name: str) -> Optional[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM cities WHERE name=?", (name,))
        row = await cur.fetchone()
    return int(row[0]) if row else None

async def upsert_forecast(city_id: int, forecast_date: str, hourly: dict[str, Any]) -> None:
    payload = json.dumps(hourly, ensure_ascii=False)
    updated_at = utcnow_iso()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO forecasts(city_id, forecast_date, updated_at, data_json)
            VALUES(?,?,?,?)
            ON CONFLICT(city_id, forecast_date)
            DO UPDATE SET updated_at=excluded.updated_at, data_json=excluded.data_json
            """,
            (city_id, forecast_date, updated_at, payload),
        )
        await db.commit()

async def get_today_hourly(city_id: int) -> Optional[dict[str, Any]]:
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT data_json FROM forecasts WHERE city_id=? AND forecast_date=?",
            (city_id, today),
        )
        row = await cur.fetchone()
    return json.loads(row[0]) if row else None