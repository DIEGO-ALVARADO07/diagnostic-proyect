from pathlib import Path
from typing import Any

import fastexcel
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from auth.dependencies import CurrentAccount
from auth.role import Role
from excel_provider.service import SheetSelectionError, read_first_sheet

MAX_UPLOAD_BYTES = 30 * 1024 * 1024
ALLOWED_EXTENSIONS = {".xlsx", ".xlsm", ".xls", ".ods"}

router = APIRouter(prefix="/excel", tags=["excel"])


@router.post("/read", status_code=status.HTTP_200_OK)
async def upload_and_read_excel(
    account: CurrentAccount,
    file: UploadFile = File(...),
    sheet_name: str | None = Form(default=None),
) -> dict[str, Any]:
    if Role(account.role) not in {Role.INSTRUCTOR, Role.SUPERADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo instructor y superadmin pueden subir archivos Excel.",
        )

    filename = file.filename or ""
    if Path(filename).suffix.casefold() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Formato no válido. Usa .xlsx, .xlsm, .xls o .ods.",
        )

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El archivo supera el límite de 30 MB.",
        )

    try:
        return await run_in_threadpool(
            read_first_sheet, content, Path(filename).name, sheet_name
        )
    except SheetSelectionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": str(error),
                "available_sheets": error.available_sheets,
            },
        ) from None
    except (fastexcel.FastExcelError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se pudo leer el libro Excel o no contiene hojas válidas.",
        ) from None
