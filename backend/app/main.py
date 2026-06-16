from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.puzzles import router as puzzles_router


def create_app() -> FastAPI:
    app = FastAPI(title="Patches Backend")
    app.include_router(health_router)
    app.include_router(puzzles_router)
    return app


app = create_app()
