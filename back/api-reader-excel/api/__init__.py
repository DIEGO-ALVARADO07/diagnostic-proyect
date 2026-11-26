from fastapi import APIRouter

from modules.courses.routes import router as courses_router
from modules.excel.routes import router as excel_router
from modules.security.routes import router as auth_router
from modules.security.users.routes import router as users_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(excel_router)
router.include_router(courses_router)


@router.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
