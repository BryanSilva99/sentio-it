from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .mqtt_client import start_mqtt_listener
from .storage import store

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    client = start_mqtt_listener()
    try:
        yield
    finally:
        client.loop_stop()
        client.disconnect()


app = FastAPI(title="Sentio-IT API", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def dashboard():
    return FileResponse("app/static/index.html")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/latest")
def latest():
    return store.latest()


@app.get("/api/readings")
def readings(limit: int = Query(default=100, ge=1, le=500)):
    return store.readings(limit)


@app.get("/api/summary")
def summary():
    return store.summary()

