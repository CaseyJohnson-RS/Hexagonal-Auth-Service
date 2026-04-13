from fastapi import APIRouter

from .auth import router as auth_router
from .events import router as events_router

router = APIRouter()
router.include_router(auth_router, prefix="/auth/api")
router.include_router(events_router, prefix="/auth/audit")
