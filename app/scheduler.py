from __future__ import annotations

import asyncio
import random
from datetime import date

from app.config import UPDATE_INTERVAL_SECONDS, MAX_CONCURRENT_UPDATES
from app.open_meteo import fetch_today_hourly
from app.repo import list_city_rows_with_today_updated, is_stale, upsert_forecast

async def updater_loop() -> None:
    sem = asyncio.Semaphore(MAX_CONCURRENT_UPDATES)

    while True:
        today = date.today().isoformat()
        rows = await list_city_rows_with_today_updated()
        if not rows:
            await asyncio.sleep(UPDATE_INTERVAL_SECONDS)
            continue

        async def one(city_id: int, lat: float, lon: float, updated_at: str | None):
            if not is_stale(updated_at):
                return
            async with sem:
                await asyncio.sleep(random.uniform(0, 0.25))
                hourly = await fetch_today_hourly(lat, lon)
                await upsert_forecast(city_id, today, hourly)

        await asyncio.gather(*(one(cid, la, lo, upd) for (cid, la, lo, upd) in rows),
                             return_exceptions=True)

        await asyncio.sleep(UPDATE_INTERVAL_SECONDS)