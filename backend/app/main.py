from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.uploads import router as uploads_router


def create_app() -> FastAPI:
    app = FastAPI(title="Patches Backend")
    app.include_router(health_router)
    app.include_router(uploads_router)
    return app


app = create_app()
