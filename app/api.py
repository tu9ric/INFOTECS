from fastapi import APIRouter, HTTPException, Query
import aiosqlite
from datetime import date

from app.schemas import CityIn, normalize_city_name
from app.open_meteo import get_current_weather, fetch_today_hourly, search_cities
from app.forecast import normalize_time_to_today_iso, parse_fields, pick_at_time
from app.repo import insert_city, list_cities, get_city_id, upsert_forecast, get_today_hourly

router = APIRouter()

@router.get("/weather/current")
async def weather_current(lat: float, lon: float):
    try:
        return await get_current_weather(lat, lon)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@router.get("/weather/at")
async def weather_at(city: str, time: str, fields: str | None = None):
    city = normalize_city_name(city)
    if not city:
        raise HTTPException(400, "City is empty")

    city_id = await get_city_id(city)
    if city_id is None:
        raise HTTPException(404, "City not found")

    hourly = await get_today_hourly(city_id)
    if hourly is None:
        raise HTTPException(404, "No forecast stored for today yet")

    iso_time = normalize_time_to_today_iso(time)
    fields_set = parse_fields(fields)
    return pick_at_time(hourly, iso_time, fields_set)

@router.get("/cities")
async def cities():
    return await list_cities()

@router.get("/cities/catalog")
async def catalog_cities(q: str = Query(..., description="City name query"),count: int = Query(10, ge=1, le=50),language: str = Query("ru"),):
    q = q.strip()
    if not q:
        raise HTTPException(400, "q is empty")
    try:
        return await search_cities(q, count=count, language=language)
    except Exception as e:
        raise HTTPException(502, str(e))
    
@router.post("/cities")
async def add_city(city: CityIn):
    try:
        city_id = await insert_city(city.name, city.lat, city.lon)
    except aiosqlite.IntegrityError:
        raise HTTPException(409, "City already exists")

    try:
        hourly = await fetch_today_hourly(city.lat, city.lon)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    today = date.today().isoformat()
    await upsert_forecast(city_id, today, hourly)
    return {"status": "ok", "city": city.name}