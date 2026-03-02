# Асинхронный REST-сервис на Python, который:
- получает **текущую погоду** по координатам (Open-Meteo),
- позволяет **добавлять города** в отслеживаемые,
- хранит **прогноз на текущий день** для отслеживаемых городов,
- **обновляет прогноз каждые 15 минут** автоматически,
- отдаёт прогноз **на сегодня в указанное время** и **по выбранным полям**,
- (дополнительно) поддерживает **пользователей**: у каждого пользователя свой список городов + управление им.


## Стек технологий
- Python 3.11+ (рекомендуется 3.12)
- FastAPI + Uvicorn
- httpx (async)
- SQLite + aiosqlite
- Open-Meteo Forecast API
- Open-Meteo Geocoding API (поиск городов)

## Run
```bash
git clone <https://github.com/tu9ric/INFOTECS>
cd INFOTECS

## Активация виртуального окружения
python -m venv .venv
.\.venv\Scripts\Activate.ps1

## Установка зависимостей
pip install -r requirements.txt

## Запуск сервиса
python3 script.py


## API
GET /health
- Проверка работоспособности сервиса

GET /weather/current
- Получение текущей погоды по координатам из open-meteo

Query-параметры:
lat (float) — широта [-90..90]
lon (float) — долгота [-180..180]

Пример:

/weather/current?lat=55.75&lon=37.61

Возможные ошибки:
422 — нет/неверные lat/lon
502 — ошибка обращения к Open-Meteo