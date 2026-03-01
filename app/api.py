from fastapi import APIRouter, HTTPException, Query, Depends
import aiosqlite
from datetime import date

from app.schemas import CityIn, UserIn, normalize_city_name, WeatherAtQuery, normalize_city_name
from app.open_meteo import get_current_weather, fetch_today_hourly, search_cities
from app.forecast import normalize_time_to_today_iso, parse_fields, pick_at_time

from app.repo import (
    insert_user, user_exists,
    insert_city, get_city_id, get_city_coords,
    link_user_city, list_user_cities, user_has_city,
    upsert_forecast, get_today_hourly, 
    unlink_user_city, list_users, delete_user
)

router = APIRouter()

@router.get("/users")
async def users():
    return await list_users()

#registration
@router.post("/users/register")
async def register_user(user: UserIn):
    try:
        user_id = await insert_user(user.username)
    except aiosqlite.IntegrityError:
        raise HTTPException(409, "Username already exists")
    return {"user_id": user_id, "username": user.username}

#delete city from user
@router.delete("/users/{user_id}/cities/{city}")
async def remove_city_for_user(user_id: int, city: str): 
    if not await user_exists(user_id):
        raise HTTPException(404, "User not found")
    
    city = normalize_city_name(city)
    if not city:
        raise HTTPException(400, "City is empty")
    
    city_id = await get_city_id(city)
    if city_id is None:
        raise HTTPException(404, "City not found")
    
    deleted = await unlink_user_city(user_id, city_id)
    if deleted == 0:
        raise HTTPException(404, "City is not in user's list")
    
    return {"status": "ok", "user_id": user_id, "removed_id": city}

#delete user
@router.delete("/user/{user_id}")
async def remove_user(user_id: int):
    deleted = await delete_user(user_id)
    if deleted == 0:
        raise HTTPException(404, "User not found")
    return {"status": "ok", "deleted_user_id": user_id}


#city to concreet user
@router.post("/users/{user_id}/cities")
async def add_city_for_user(user_id: int, city: CityIn):
    if not await user_exists(user_id):
        raise HTTPException(404, "User not found")

    city_id = await get_city_id(city.name)
    if city_id is None:
        try: 
            city_id = await insert_city(city.name, city.lat, city.lon)
        except aiosqlite.IntegrityError:
            # while paste, someone pasted faster
            city_id = await get_city_id(city.name)
            if city_id is None:
                raise HTTPException(500, "Failed to create city")
            
    await link_user_city(user_id, city_id)

    try:
        hourly = await fetch_today_hourly(city.lat, city.lon)
    except Exception as e:
        raise HTTPException(502, str(e))
    
    today = date.today().isoformat()
    await upsert_forecast(city_id, today, hourly)

    return {"status": "ok", "user_id": user_id, "city": city.name}

# list of cities concreet user
@router.get("/users/{user_id}/cities")
async def cities_for_user(user_id: int):
    if not await user_exists(user_id):
        raise HTTPException(404, "User not found")
    return await list_user_cities(user_id)


# weather in concreet time for the city of user
@router.get("/users/{user_id}/weather/at")
async def weather_at_for_user(user_id: int, q: WeatherAtQuery = Depends()):
    if not await user_exists(user_id):
        raise HTTPException(404, "User not found")
    
    city = normalize_city_name(city)
    if not city:
        raise HTTPException(400, "City is empty")

    city_id = await get_city_id(city)
    if city_id is None:
        raise HTTPException(404, "City not found")

    if not await user_has_city(user_id, city_id):
        raise HTTPException(403, "City is not in user's list")

    hourly = await get_today_hourly(city_id)
    if hourly is None:
        raise HTTPException(404, "No forecast stored for today yet")

    iso_time = normalize_time_to_today_iso(q.time)
    fields_set = parse_fields(q.fields)
    return pick_at_time(hourly, iso_time, fields_set)

@router.get("/weather/current")
async def weather_current(lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180)):
    try:
        return await get_current_weather(lat, lon)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@router.get("/weather/at")
async def weather_at(q: WeatherAtQuery = Depends()):
    city = normalize_city_name(city)
    if not city:
        raise HTTPException(400, "City is empty")

    city_id = await get_city_id(q.city)
    if city_id is None:
        raise HTTPException(404, "City not found")

    hourly = await get_today_hourly(city_id)
    if hourly is None:
        raise HTTPException(404, "No forecast stored for today yet")

    iso_time = normalize_time_to_today_iso(q.time)
    fields_set = parse_fields(q.fields)
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