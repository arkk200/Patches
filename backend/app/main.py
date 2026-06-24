from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.puzzles import router as puzzles_router
from app.database import Base, engine
from app.models import PuzzleResult  # noqa: F401 — register model metadata


@asynccontextmanager
async def lifespan(application: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Patches Backend", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(puzzles_router)
    return app


app = create_app()
