from fastapi import APIRouter

from auth.routes import router as auth_router
from excel_provider.routes import router as excel_router
from users.routes import router as users_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(excel_router)


@router.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
