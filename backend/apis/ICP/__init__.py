# backend/apis/ICP/__init__.py
from fastapi import APIRouter
from .generate_ICP import router as icp_generate_router
# from .get_icp_lead_detail import router as icp_detail_router
from .icp_lead_analysis import router as icp_lead_analysis_router
from .get_ideal_snapshot import router as icp_snapshot_router


from .generate_icp_insight import router as icp_insight_router

router = APIRouter()
router.include_router(icp_generate_router)
# router.include_router(icp_detail_router)
router.include_router(icp_lead_analysis_router)
router.include_router(icp_snapshot_router)


router.include_router(icp_insight_router)

