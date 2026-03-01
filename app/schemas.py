from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List

def normalize_spaces(s: str) -> str:
    return " ".join((s or "").strip().split())\
    
def normalize_lower(s: str) -> str:
    return normalize_spaces(s).lower()

def normalize_city_name(name: str) -> str:
    return " ".join((name or "").strip().split())

def normalize_username(s: str) -> str:
    return normalize_lower(s)

def normalize_fields(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    items = [x.strip().lower() for x in s.split(",") if x.strip()]
    return ",".join(items) if items else ""

class CityIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)

    @field_validator("name")
    @classmethod
    def _norm_name(cls, v: str) -> str:
        v = normalize_city_name(v)
        if not v:
            raise ValueError("City name is empty")
        return v
    
class UserIn(BaseModel):
    username: str = Field(min_length=1, max_length=50)

    @field_validator("username")
    @classmethod
    def _norm_username(cls, v: str) -> str:
        v = normalize_username(v)
        if not v:
            raise ValueError("Username is empty")
        return v
    

class WeatherAtQuery(BaseModel):
    city: str
    time: str
    fields: Optional[str] = None

    @field_validator("city")
    @classmethod
    def _norm_city(cls, v:str) -> str:
        v = normalize_city_name(v)
        if not v:
            raise ValueError("City is empty")
        return v
    
    @field_validator("time")
    @classmethod
    def _norm_time(cls, v:str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("time is empty")
        return v
    
    @field_validator("fields")
    @classmethod
    def _norm_fields(cls, v:Optional[str]) -> Optional[str]:
        return normalize_fields(v)