import io
import zipfile
from xml.sax.saxutils import escape

import unittest
from hashlib import sha256

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app import app
from core.exceptions import ApplicationError
from modules.excel.entities.academic import (
    AcademicResult,
    DashboardState,
    ExcelImport,
    TdProgramasReference,
)
from modules.excel.dtos.requests.dashboard import DashboardFilterQuery
from modules.excel.dtos.requests.read_workbook import ReadWorkbookRequest
from modules.excel.repositories.dashboard_repository import (
    DashboardWorkbookRepository,
)
from modules.excel.routes import router as excel_router
from modules.excel.services.dashboard_metrics import classify_level
from modules.excel.services.dashboard_service import DashboardService
from modules.security.entities import Account, AuthBase
from modules.security.entities.role import Role


BD_HEADERS = [
    "Usuario",
    "Nombre",
    "Apellido(s)",
    "Dirección de correo",
    "Lectura crítica",
    "Comunicación escrita",
    "Competencias ciudadanas",
    "Razonamiento cuantitativo",
    "Inglés",
    "GLOBAL",
    "Programa",
    "Momento",
    "TIPO",
    "SEMESTRE",
    "AÑO",
    "SIM",
    "n: Lectura crítica",
    "n: Comunicación escrita",
    "n: Competencias ciudadanas",
    "n: Razonamiento cuantitativo",
    "n: Inglés",
    "SEDE",
    "GRUPO",
    "APLICA SIMULACRO",
    "APLICO ENTRENAMIENTO",
    "ENT",
]


def _column_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _cell_xml(reference: str, value: object) -> str:
    if value is None:
        return f'<c r="{reference}"/>'
    if isinstance(value, (int, float)):
        return f'<c r="{reference}"><v>{value}</v></c>'
    return (
        f'<c r="{reference}" t="inlineStr"><is><t>'
        f"{escape(str(value))}</t></is></c>"
    )


def _sheet_xml(rows: list[list[object]]) -> str:
    xml_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = "".join(
            _cell_xml(f"{_column_name(column_index)}{row_index}", value)
            for column_index, value in enumerate(row, start=1)
        )
        xml_rows.append(f'<row r="{row_index}">{cells}</row>')
    return (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(xml_rows)}</sheetData></worksheet>"
    )


def make_dashboard_workbook(global_score: object = 90) -> bytes:
    first_record = [
        "101",
        "Ana",
        "Pérez",
        "ana@example.com",
        100,
        110,
        120,
        130,
        140,
        global_score,
        "PROGRAMA Á",
        None,
        "SABER PRO",
        "SEMESTRE 7",
        2025,
        "SIMULACRO 2025-1 MOMENTO 1",
        None,
        None,
        None,
        None,
        None,
        None,
        "MOMENTO 1",
        "Si",
        None,
        "A",
    ]
    second_record = [
        "101",
        "Ana",
        "Pérez",
        "ana@example.com",
        150,
        "N",
        180,
        160,
        180,
        134,
        "Programa A",
        None,
        "SABER PRO",
        "SEMESTRE 8",
        2026,
        "SIMULACRO 2026-1 MOMENTO 2",
        None,
        None,
        None,
        None,
        None,
        None,
        "MOMENTO 2",
        "Si",
        None,
        None,
    ]
    non_presented = [
        "102",
        "Luis",
        "Gómez",
        "luis@example.com",
        100,
        100,
        100,
        100,
        100,
        100,
        "PROGRAMA A",
        None,
        "SABER PRO",
        "SEMESTRE 7",
        2025,
        "SIMULACRO 2025-1 MOMENTO 1",
        None,
        None,
        None,
        None,
        None,
        None,
        "MOMENTO 1",
        "No",
        None,
        None,
    ]
    td_rows = [
        ["TD", "LC", "CE", "CC", "RC", "I", "GL", "GL"],
        ["AÑO", 2025, None, None, None, None, None, None],
        ["PROGRAMA", "LC", "CE", "CC", "RC", "I", "GL", "GL"],
        ["SIMULACRO 2025-1 MOMENTO 1", None, None, None, None, None, None, None],
        ["PROGRAMA A", 100, 110, 120, 130, 140, 120, 120],
    ]
    sheets = [
        ("BD GEN", [BD_HEADERS, first_record, second_record, non_presented]),
        ("TD PROGRAMAS", td_rows),
        ("IGNORAR", [["Auxiliar"], ["no debe procesarse"]]),
    ]
    contents = [
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + "".join(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for index in range(1, len(sheets) + 1)
        )
        + "</Types>",
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>",
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>"
        + "".join(
            f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
            for index, (name, _) in enumerate(sheets, start=1)
        )
        + "</sheets></workbook>",
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(
            f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
            for index in range(1, len(sheets) + 1)
        )
        + "</Relationships>",
    ]
    workbook = io.BytesIO()
    with zipfile.ZipFile(workbook, "w") as archive:
        archive.writestr("[Content_Types].xml", contents[0])
        archive.writestr("_rels/.rels", contents[1])
        archive.writestr("xl/workbook.xml", contents[2])
        archive.writestr("xl/_rels/workbook.xml.rels", contents[3])
        for index, (_, rows) in enumerate(sheets, start=1):
            archive.writestr(
                f"xl/worksheets/sheet{index}.xml",
                _sheet_xml(rows),
            )
    return workbook.getvalue()


class DashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        AuthBase.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.instructor = Account(
            id=1,
            username="instructor",
            email="instructor@example.com",
            full_name="Instructor",
            password_hash="unused",
            role=Role.INSTRUCTOR.value,
            is_active=True,
        )
        self.db.add(self.instructor)
        self.db.add(DashboardState(id=1))
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_reads_only_the_two_dashboard_sheets(self) -> None:
        workbook = DashboardWorkbookRepository().read_sheets(
            make_dashboard_workbook()
        )

        self.assertIn("IGNORAR", workbook.available_sheets)
        self.assertEqual(len(workbook.bd_gen_rows), 3)
        self.assertEqual(
            workbook.bd_gen_rows[0]["programa"],
            "PROGRAMA Á",
        )
        self.assertEqual(len(workbook.td_programas_rows), 4)

    def test_import_calculates_metrics_and_keeps_student_history(self) -> None:
        service = DashboardService()
        response = service.import_workbook(
            ReadWorkbookRequest(
                filename="results.xlsm",
                content=make_dashboard_workbook(),
            ),
            self.instructor,
            self.db,
        )

        self.assertEqual(response.filters.years, [2025, 2026])
        self.assertEqual(response.overview.kpis.presentations, 2)
        self.assertEqual(response.overview.kpis.unique_students, 1)
        self.assertEqual(response.overview.kpis.not_presented_records, 1)
        self.assertEqual(response.overview.kpis.average_global, 112)
        self.assertEqual(response.source_audit.td_programas_visible_year, 2025)
        self.assertEqual(response.source_audit.difference_count, 0)
        self.assertLessEqual(len(response.overview.programs), 50)
        self.assertEqual(
            {program.name for program in response.filters.programs},
            {"PROGRAMA Á", "Programa A", "PROGRAMA A"},
        )
        stored_result = self.db.scalar(
            select(AcademicResult).where(
                AcademicResult.import_id == response.import_id,
                AcademicResult.source_row_number == 2,
            )
        )
        self.assertEqual(stored_result.global_score, 90)
        self.assertEqual(stored_result.global_calculated_score, 120)

        program = next(
            item
            for item in response.filters.programs
            if item.name == "PROGRAMA Á"
        )
        program_response = service.get_program(
            self.db,
            response.import_id,
            program.program_id,
            DashboardFilterQuery(year=2025),
            search="ana",
            page=1,
            page_size=50,
        )
        self.assertEqual(len(program_response.students), 1)
        self.assertEqual(program_response.students[0].document, "101")
        self.assertEqual(program_response.students[0].global_score, 90)
        self.assertEqual(program_response.metrics.average_global, 90)

        student = service.get_student(self.db, response.import_id, "101")
        self.assertEqual([attempt.year for attempt in student.history], [2025, 2026])
        self.assertEqual(
            student.history[0].program_average_global,
            90,
        )
        self.assertEqual(
            student.history[1].levels["comunicacion_escrita"],
            "Sin resultado",
        )
        self.assertEqual(student.changes["global"], "mejora")

    def test_import_hash_is_idempotent_and_activation_keeps_history(self) -> None:
        service = DashboardService()
        content = make_dashboard_workbook()
        first = service.import_workbook(
            ReadWorkbookRequest(filename="first.xlsx", content=content),
            self.instructor,
            self.db,
        )
        repeated = service.import_workbook(
            ReadWorkbookRequest(filename="renamed.xlsx", content=content),
            self.instructor,
            self.db,
        )
        self.assertEqual(repeated.import_id, first.import_id)
        self.assertEqual(
            self.db.scalar(select(ExcelImport).where(ExcelImport.id == first.import_id)).status,
            "ACTIVE",
        )

        updated_content = make_dashboard_workbook(global_score=91)
        second = service.import_workbook(
            ReadWorkbookRequest(filename="updated.xlsx", content=updated_content),
            self.instructor,
            self.db,
        )
        self.assertNotEqual(second.import_id, first.import_id)
        self.assertEqual(
            self.db.scalar(select(ExcelImport).where(ExcelImport.id == first.import_id)).status,
            "HISTORICAL",
        )
        self.assertEqual(
            self.db.scalar(select(ExcelImport).where(ExcelImport.id == second.import_id)).status,
            "ACTIVE",
        )
        self.assertEqual(
            service.get_active_import(self.db).import_id,
            second.import_id,
        )
        history = service.list_imports(self.db, limit=20)
        self.assertEqual(history.active_import_id, second.import_id)
        self.assertEqual(
            {item.status for item in history.imports},
            {"ACTIVE", "HISTORICAL"},
        )
        self.assertEqual(
            self.db.scalar(
                select(AcademicResult.global_score).where(
                    AcademicResult.import_id == second.import_id,
                    AcademicResult.source_row_number == 2,
                )
            ),
            91,
        )

    def test_soft_deletes_history_and_hides_it_from_normal_queries(self) -> None:
        service = DashboardService()
        historical = service.import_workbook(
            ReadWorkbookRequest(
                filename="first.xlsx",
                content=make_dashboard_workbook(),
            ),
            self.instructor,
            self.db,
        )
        active = service.import_workbook(
            ReadWorkbookRequest(
                filename="second.xlsx",
                content=make_dashboard_workbook(global_score=91),
            ),
            self.instructor,
            self.db,
        )

        with self.assertRaises(ApplicationError) as instructor_error:
            service.get_overview(
                self.db,
                historical.import_id,
                DashboardFilterQuery(),
                page=1,
                page_size=50,
                account=self.instructor,
            )
        self.assertEqual(instructor_error.exception.status_code, 404)
        superadmin = Account(
            id=2,
            username="admin",
            email="admin@example.com",
            full_name="Super Admin",
            password_hash="unused",
            role=Role.SUPERADMIN.value,
            is_active=True,
        )
        self.assertEqual(
            service.get_overview(
                self.db,
                historical.import_id,
                DashboardFilterQuery(),
                page=1,
                page_size=50,
                account=superadmin,
            ).import_id,
            historical.import_id,
        )

        service.delete_import(self.db, historical.import_id)

        deleted = self.db.get(ExcelImport, historical.import_id)
        self.assertIsNotNone(deleted)
        self.assertIsNotNone(deleted.deleted_at)
        self.assertEqual(deleted.status, "HISTORICAL")
        self.assertIsNotNone(
            self.db.scalar(
                select(AcademicResult.id).where(
                    AcademicResult.import_id == historical.import_id
                )
            )
        )
        self.assertIsNotNone(
            self.db.scalar(
                select(TdProgramasReference.id).where(
                    TdProgramasReference.import_id == historical.import_id
                )
            )
        )
        self.assertEqual(
            service.get_active_import(self.db).import_id,
            active.import_id,
        )
        self.assertEqual(
            self.db.scalar(
                select(AcademicResult.global_score).where(
                    AcademicResult.import_id == active.import_id,
                    AcademicResult.source_row_number == 2,
                )
            ),
            91,
        )
        self.assertNotIn(
            historical.import_id,
            {item.import_id for item in service.list_imports(self.db, 100).imports},
        )
        admin_history = service.list_admin_imports(self.db, 100)
        deleted_entry = next(
            item
            for item in admin_history.imports
            if item.import_id == historical.import_id
        )
        self.assertEqual(deleted_entry.status, "DELETED")
        self.assertIsNotNone(deleted_entry.deleted_at)

        with self.assertRaises(ApplicationError) as deleted_error:
            service.get_overview(
                self.db,
                historical.import_id,
                DashboardFilterQuery(),
                page=1,
                page_size=50,
            )
        self.assertEqual(deleted_error.exception.status_code, 404)

    def test_can_soft_deactivate_active_import_and_reject_missing_import(self) -> None:
        service = DashboardService()
        active = service.import_workbook(
            ReadWorkbookRequest(
                filename="active.xlsx",
                content=make_dashboard_workbook(),
            ),
            self.instructor,
            self.db,
        )

        service.delete_import(self.db, active.import_id)

        deleted = self.db.get(ExcelImport, active.import_id)
        self.assertIsNotNone(deleted)
        self.assertIsNotNone(deleted.deleted_at)
        self.assertIsNotNone(
            self.db.scalar(
                select(AcademicResult.id).where(
                    AcademicResult.import_id == active.import_id
                )
            )
        )
        with self.assertRaises(ApplicationError) as no_active_error:
            service.get_active_import(self.db)
        self.assertEqual(no_active_error.exception.status_code, 404)

        with self.assertRaises(ApplicationError) as missing_error:
            service.delete_import(self.db, "missing-import")
        self.assertEqual(missing_error.exception.status_code, 404)

    def test_non_numeric_global_remains_null(self) -> None:
        content = make_dashboard_workbook(global_score=None)
        service = DashboardService()
        response = service.import_workbook(
            ReadWorkbookRequest(filename="null-global.xlsx", content=content),
            self.instructor,
            self.db,
        )
        self.assertEqual(response.overview.kpis.average_global, 134)
        student = service.get_student(self.db, response.import_id, "101")
        self.assertIsNone(student.history[0].global_score)

    def test_dashboard_endpoints_require_bearer_authentication(self) -> None:
        paths = app.openapi()["paths"]
        dashboard_operations = [
            operation
            for path, methods in paths.items()
            if path.startswith("/excel/dashboard")
            for operation in methods.values()
        ]

        self.assertEqual(len(dashboard_operations), 8)
        for operation in dashboard_operations:
            with self.subTest(operation=operation["operationId"]):
                self.assertIn({"HTTPBearer": []}, operation["security"])

    def test_import_deletion_is_superadmin_only(self) -> None:
        delete_route = next(
            route
            for route in excel_router.routes
            if getattr(route, "path", None)
            == "/excel/dashboard/imports/{import_id}"
            and "DELETE" in route.methods
        )
        role_guard = delete_route.dependant.dependencies[0].call

        with self.assertRaises(ApplicationError) as error:
            role_guard(self.instructor)
        self.assertEqual(error.exception.status_code, 403)

        superadmin = Account(
            id=2,
            username="admin",
            email="admin@example.com",
            full_name="Super Admin",
            password_hash="unused",
            role=Role.SUPERADMIN.value,
            is_active=True,
        )
        self.assertIs(role_guard(superadmin), superadmin)

        list_route = next(
            route
            for route in excel_router.routes
            if getattr(route, "path", None) == "/excel/dashboard/admin/imports"
            and "GET" in route.methods
        )
        list_role_guard = list_route.dependant.dependencies[0].call
        with self.assertRaises(ApplicationError) as list_error:
            list_role_guard(self.instructor)
        self.assertEqual(list_error.exception.status_code, 403)
        self.assertIs(list_role_guard(superadmin), superadmin)

        history_route = next(
            route
            for route in excel_router.routes
            if getattr(route, "path", None) == "/excel/dashboard/imports"
            and "GET" in route.methods
        )
        history_role_guard = history_route.dependant.dependencies[0].call
        with self.assertRaises(ApplicationError) as history_error:
            history_role_guard(self.instructor)
        self.assertEqual(history_error.exception.status_code, 403)
        self.assertIs(history_role_guard(superadmin), superadmin)

    def test_rejects_invalid_workbooks_and_page_sizes(self) -> None:
        service = DashboardService()
        with self.assertRaises(ApplicationError) as error:
            service.import_workbook(
                ReadWorkbookRequest(
                    filename="invalid.xlsx",
                    content=b"not an Excel workbook",
                ),
                self.instructor,
                self.db,
            )
        self.assertEqual(error.exception.status_code, 422)
        failed_import = self.db.scalar(
            select(ExcelImport).where(
                ExcelImport.file_sha256
                == sha256(b"not an Excel workbook").hexdigest()
            )
        )
        self.assertIsNotNone(failed_import)
        self.assertEqual(failed_import.status, "FAILED")

        response = service.import_workbook(
            ReadWorkbookRequest(
                filename="results.xlsm",
                content=make_dashboard_workbook(),
            ),
            self.instructor,
            self.db,
        )
        with self.assertRaises(ApplicationError) as error:
            service.get_overview(
                self.db,
                response.import_id,
                DashboardFilterQuery(),
                page=1,
                page_size=51,
            )
        self.assertEqual(error.exception.status_code, 422)

    def test_levels_cover_each_competency_boundary(self) -> None:
        expected = (
            ((124, "1"), (125, "2"), (156, "2"), (157, "3"), (198, "3"), (199, "4")),
            ((114, "1"), (115, "2"), (148, "2"), (149, "3"), (182, "3"), (183, "4")),
            ((125, "1"), (126, "2"), (156, "2"), (157, "3"), (198, "3"), (199, "4")),
            ((125, "1"), (126, "2"), (153, "2"), (154, "3"), (201, "3"), (202, "4")),
            ((120, "A1"), (121, "A2"), (164, "A2"), (165, "B1"), (195, "B1"), (196, "B2")),
        )
        for competency_index, boundaries in enumerate(expected):
            for score, level in boundaries:
                with self.subTest(competency=competency_index, score=score):
                    self.assertEqual(
                        classify_level(competency_index, score),
                        level,
                    )
        self.assertIsNone(classify_level(0, None))


if __name__ == "__main__":
    unittest.main()
