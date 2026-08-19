from fastapi import APIRouter
from .enrichment import router as enrichment_router
router = APIRouter()
router.include_router(enrichment_router)