from __future__ import annotations

import json
from datetime import datetime, date, timezone
from typing import Any, Optional, Tuple

import aiosqlite
from app.config import DB_PATH, UPDATE_INTERVAL_SECONDS

def utcnow_iso() -> str:
    return datetime.utcnow().isoformat()

# ----------------------------------------------USERS--------------------------------
async def list_users() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, username, created_at FROM users ORDER BY id"
        )
        rows = await cur.fetchall()
    return [{"id": uid, "username": uname, "created_at": created} for (uid, uname, created) in rows]

async def delete_user(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys=ON;")
        await db.execute("DELETE FROM user_cities WHERE user_id=?", (user_id,))
        cur = await db.execute("DELETE FROM users WHERE id=?", (user_id,))
        await db.commit()
        return cur.rowcount

async def insert_user(username: str) -> int:
    now = utcnow_iso()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO users(username, created_at) VALUES(?,?)", 
            (username, now),
        )
        await db.commit()
        return cur.lastrowid

async def user_exists(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT 1 FROM users WHERE id=?", (user_id,))
        row = await cur.fetchone()
    return row is not None


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


async def unlink_user_city(user_id: int, city_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM user_cities WHERE user_id=? AND city_id=?",
            (user_id, city_id),
        )
        await db.commit()
        return cur.rowcount

# ----------------------------------- user_cities ----------------------
async def get_city_coords(city_id: int) -> tuple[float, float] | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT lat, lon FROM cities WHERE id=?", (city_id,))
        row = await cur.fetchone()
    if not row:
        return None
    return float(row[0]), float(row[1])

async def link_user_city(user_id: int, city_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO user_cities(user_id, city_id) VALUES(?,?)",
            (user_id, city_id),
        )
        await db.commit()


async def user_has_city(user_id: int, city_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM user_cities WHERE user_id=? AND city_id=?",
            (user_id, city_id),
        )
        row = await cur.fetchone()
    return row is not None

async def list_user_cities(user_id: int) -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT c.name, c.lat, c.lon
            FROM cities c
            JOIN user_cities uc ON uc.city_id = c.id
            WHERE uc.user_id = ?
            ORDER BY c.name
            """,
            (user_id,),
        )
        rows = await cur.fetchall()
    return [{"name": n, "lat": la, "lon": lo} for (n, la, lo) in rows]



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