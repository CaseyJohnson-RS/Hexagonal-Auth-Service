import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.adapters.inbound.http.routers import router as api_router
from app.adapters.nexus import get_redis_client
from app.config.settings import settings


logging.basicConfig(level=settings.logging_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup.")
    yield
    logger.info("Application shutdown — closing Redis connection.")
    await get_redis_client().aclose()


app = FastAPI(lifespan=lifespan)
app.include_router(api_router)
