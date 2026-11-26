from fastapi import APIRouter, Depends, status
from fastapi.concurrency import run_in_threadpool
from starlette.responses import Response

from core.db_session import DbSession
from modules.courses.dtos import (
    CourseCreateRequest,
    CourseEnrollRequest,
    CourseEnrollResponse,
    CourseListResponse,
    CourseResponse,
    CourseStudentsResponse,
    DeletedCoursesResponse,
)
from modules.courses.service import CourseService
from modules.excel.routes import dashboard_service
from modules.security.dependencies import CurrentAccount, require_roles
from modules.security.entities.role import Role

_TEACHERS = [Depends(require_roles(Role.INSTRUCTOR, Role.SUPERADMIN))]
_ADMIN = [Depends(require_roles(Role.SUPERADMIN))]

router = APIRouter(prefix="/courses", tags=["courses"])
# Comparte la caché de datasets del dashboard (los niveles salen de ahí).
course_service = CourseService(dashboard_service.student_levels)


@router.get("", response_model=CourseListResponse, dependencies=_TEACHERS)
async def list_courses(db: DbSession) -> CourseListResponse:
    """Cursos activos en los 4 niveles, con los estudiantes disponibles por materia."""
    return await run_in_threadpool(course_service.list_courses, db)


@router.post(
    "",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=_TEACHERS,
)
async def create_course(
    db: DbSession, account: CurrentAccount, body: CourseCreateRequest
) -> CourseResponse:
    """Crea un curso con nivel (1–4), materia, nombre, descripción y metodología."""
    return await run_in_threadpool(
        course_service.create_course,
        db,
        account,
        body.name,
        body.level,
        body.competency,
        body.description,
        body.methodology,
    )


@router.get("/deleted", response_model=DeletedCoursesResponse, dependencies=_ADMIN)
async def list_deleted_courses(db: DbSession) -> DeletedCoursesResponse:
    """Cursos eliminados con toda su información (solo superadmin)."""
    return await run_in_threadpool(course_service.deleted_courses, db)


@router.delete("/{course_id}", response_model=CourseResponse, dependencies=_TEACHERS)
async def delete_course(
    db: DbSession, account: CurrentAccount, course_id: int
) -> CourseResponse:
    """Eliminación lógica: el curso y sus inscripciones se conservan (auditoría)."""
    return await run_in_threadpool(course_service.delete_course, db, course_id, account)


@router.post("/{course_id}/restore", response_model=CourseResponse, dependencies=_ADMIN)
async def restore_course(
    db: DbSession, account: CurrentAccount, course_id: int
) -> CourseResponse:
    """Habilita de nuevo un curso eliminado, con sus inscripciones (solo superadmin)."""
    return await run_in_threadpool(course_service.restore_course, db, course_id, account)


@router.get(
    "/{course_id}/students",
    response_model=CourseStudentsResponse,
    dependencies=_TEACHERS,
)
async def list_course_students(db: DbSession, course_id: int) -> CourseStudentsResponse:
    """Estudiantes inscritos, con programa, nivel al inscribirse y nivel actual."""
    return await run_in_threadpool(course_service.course_students, db, course_id)


@router.post(
    "/{course_id}/enroll",
    response_model=CourseEnrollResponse,
    dependencies=_TEACHERS,
)
async def enroll_level_students(
    db: DbSession,
    account: CurrentAccount,
    course_id: int,
    body: CourseEnrollRequest,
) -> CourseEnrollResponse:
    """Agrega a todos los que tienen el nivel del curso en su materia, en ``period``.

    Sin ``period``, el último con datos; ``all`` usa el histórico. Los que ya
    estaban inscritos no se repiten.
    """
    return await run_in_threadpool(
        course_service.enroll_level, db, course_id, account, body.period
    )


@router.delete(
    "/{course_id}/students/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=_TEACHERS,
)
async def remove_course_student(
    db: DbSession, course_id: int, student_id: int
) -> Response:
    """Saca a un estudiante del curso."""
    await run_in_threadpool(course_service.remove_student, db, course_id, student_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
