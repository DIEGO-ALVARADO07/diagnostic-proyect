from fastapi import FastAPI

from api import router

def create_app() -> FastAPI:
    application = FastAPI(
        title="Diagnostic API",
        description="API modular para cuentas, roles y lectura de archivos Excel.",
        version="1.0.0",
    )
    application.include_router(router)
    return application


app = create_app()
