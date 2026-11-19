from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api import router
from core.exceptions import ApplicationError

def create_app() -> FastAPI:
    application = FastAPI(
        title="Diagnostic API",
        description="API modular para cuentas, roles y lectura de archivos Excel.",
        version="1.0.0",
    )
    application.include_router(router)

    @application.exception_handler(ApplicationError)
    async def handle_application_error(
        _request: Request, error: ApplicationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": error.detail},
            headers=error.headers,
        )

    return application


app = create_app()
