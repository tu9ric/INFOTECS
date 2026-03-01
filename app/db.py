import aiosqlite
from app.config import DB_PATH

CREATE_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS cities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  lat REAL NOT NULL,
  lon REAL NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS forecasts (
  city_id INTEGER NOT NULL,
  forecast_date TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  data_json TEXT NOT NULL,
  UNIQUE(city_id, forecast_date),
  FOREIGN KEY(city_id) REFERENCES cities(id)
);
"""

async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_SQL)
        await db.commit()