from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from modules.security.database import get_db
from modules.security.dependencies import CurrentToken
from modules.security.dtos.requests.auth import LoginRequest
from modules.security.dtos.responses.auth import LoginResponse
from modules.security.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    return AuthService(db).login(payload)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    token: CurrentToken, db: Session = Depends(get_db)
) -> Response:
    AuthService(db).logout(token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
