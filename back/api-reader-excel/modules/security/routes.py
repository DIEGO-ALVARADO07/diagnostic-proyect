from fastapi import APIRouter, Response, status

from core.db_session import DbSession
from modules.security.dependencies import CurrentToken
from modules.security.dtos.requests.auth import LoginRequest
from modules.security.dtos.responses.auth import LoginResponse
from modules.security.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: DbSession) -> LoginResponse:
    return AuthService(db).login(payload)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    token: CurrentToken, db: DbSession
) -> Response:
    AuthService(db).logout(token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
