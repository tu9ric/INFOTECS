from pydantic import BaseModel, Field, field_validator

def normalize_city_name(name: str) -> str:
    return " ".join((name or "").strip().split())

class CityIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    lat: float
    lon: float

    @field_validator("name")
    @classmethod
    def _norm_name(cls, v: str) -> str:
        v = normalize_city_name(v)
        if not v:
            raise ValueError("City name is empty")
        return v