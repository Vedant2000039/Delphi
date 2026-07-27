# /Authentication/__init__.py
from fastapi import APIRouter
from .login   import router as login_router
from .register import router as register_router
from .auth    import router as auth_router
from .forget  import router as forget_router

router = APIRouter(prefix="/auth", tags=["Authentication"])

router.include_router(login_router)
router.include_router(register_router)
router.include_router(auth_router)
router.include_router(forget_router)