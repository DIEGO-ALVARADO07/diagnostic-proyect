from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from core.db_session import DbSession
from modules.enrollment.dtos import EnrollmentListResponse, EnrollmentUploadResponse
from modules.enrollment.service import MAX_PAGE_SIZE, EnrollmentService
from modules.excel.routes import dashboard_service
from modules.excel.services.excel_service import MAX_UPLOAD_BYTES
from modules.security.dependencies import CurrentAccount, require_roles
from modules.security.entities.role import Role

PERIOD_PATTERN = r"^\d{4}-[12]$"
_ADMIN = [Depends(require_roles(Role.SUPERADMIN))]

router = APIRouter(prefix="/enrollment", tags=["enrollment"])
# Al subir matriculados cambia el programa de CORHUILA: se limpia la caché.
enrollment_service = EnrollmentService(on_change=dashboard_service.loader.cache.clear)


@router.post(
    "/import",
    response_model=EnrollmentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=_ADMIN,
)
async def import_enrollment(
    db: DbSession,
    account: CurrentAccount,
    file: UploadFile = File(...),
    period: str = Form(..., pattern=PERIOD_PATTERN),
) -> EnrollmentUploadResponse:
    """Sube el archivo de matriculados de un periodo (solo superadmin).

    Reemplaza al anterior del mismo periodo. Debe traer al menos PROGRAMA,
    IDENTIFICACION, NOMBRES y APELLIDOS; si trae COD_PERIODO, debe coincidir.
    """
    filename = enrollment_service.validate_filename(file.filename or "")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    return await run_in_threadpool(
        enrollment_service.import_file, db, account, filename, content, period
    )


@router.get("/records", response_model=EnrollmentListResponse, dependencies=_ADMIN)
async def list_enrollment_records(
    db: DbSession,
    period: str | None = Query(default=None, pattern=PERIOD_PATTERN),
    program: str | None = Query(default=None, max_length=255),
    semester: int | None = Query(default=None, ge=1, le=20),
    document_type: str | None = Query(default=None, max_length=10),
    gender: str | None = Query(default=None, max_length=10),
    stratum: int | None = Query(default=None, ge=0, le=9),
    search: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> EnrollmentListResponse:
    """Matriculados de un periodo con todas sus columnas y filtros (solo superadmin).

    Sin ``period``, el más reciente cargado. ``program`` es la clave normalizada
    que devuelve ``filters.programs``.
    """
    return await run_in_threadpool(
        enrollment_service.list_records,
        db, period, program, semester, document_type, gender, stratum, search,
        page, page_size,
    )
