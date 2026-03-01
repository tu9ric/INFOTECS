import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.db import init_db
from app.api import router
from app.scheduler import updater_loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(updater_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(lifespan=lifespan)
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "ok"}
