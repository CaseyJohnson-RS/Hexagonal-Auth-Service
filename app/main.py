from fastapi import FastAPI
from app.adapters.inbound.http.routers import router as api_router

from app.config.settings import settings

import logging


logging.basicConfig(level=settings.logging_level)
logger = logging.getLogger(__name__)


app = FastAPI()
app.include_router(api_router)
