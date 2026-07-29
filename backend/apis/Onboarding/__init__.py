from fastapi import APIRouter

from .enrichment import router as enrichment_router
from .context_builder import router as context_builder_router

router = APIRouter()

router.include_router(enrichment_router)
router.include_router(context_builder_router)