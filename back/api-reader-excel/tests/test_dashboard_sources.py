"""Fase 8: fuente, periodo, momento y un activo por espacio."""

import unittest
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from core.exceptions import ApplicationError
from core.orm import Base, utcnow
from modules.excel.dtos.requests.dashboard import DashboardFilterQuery
from modules.excel.dtos.requests.read_workbook import ReadWorkbookRequest
from modules.excel.entities.academic import (
    AcademicResult,
    ActiveImport,
    DashboardState,
    ExcelImport,
)
from modules.excel.services.dashboard_service import DashboardService
from modules.security.entities import Account
from modules.security.entities.role import Role
from tests.test_dashboard import make_dashboard_workbook


class DashboardSourcesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.admin = Account(
            id=1,
            username="admin",
            email="admin@example.com",
            full_name="Admin",
            password_hash="unused",
            role=Role.SUPERADMIN.value,
            is_active=True,
        )
        self.db.add_all([self.admin, DashboardState(id=1)])
        self.db.commit()
        self.service = DashboardService()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def _import(self, global_score: object = 90):
        return self.service.import_workbook(
            ReadWorkbookRequest(
                filename="ese.xlsx",
                content=make_dashboard_workbook(global_score=global_score),
            ),
            self.admin,
            self.db,
        )

    def _seed_corhuila(self, period: str) -> str:
        """Simula una importación activa de CORHUILA (su lector llega en la fase 10)."""
        import_id = str(uuid4())
        self.db.add(
            ExcelImport(
                id=import_id,
                filename=f"corhuila-{period}.xlsx",
                source="CORHUILA",
                period=period,
                file_sha256=uuid4().hex + uuid4().hex,
                status="ACTIVE",
                activated_at=utcnow(),
            )
        )
        self.db.add(ActiveImport(slot=f"CORHUILA:{period}", import_id=import_id))
        self.db.commit()
        return import_id

    def test_ese_rows_keep_period_and_moment_from_sim(self) -> None:
        response = self._import()

        self.assertEqual(response.source, "ESE")
        rows = self.db.execute(
            select(
                AcademicResult.source_row_number,
                AcademicResult.period,
                AcademicResult.moment,
            )
            .where(AcademicResult.import_id == response.import_id)
            .order_by(AcademicResult.source_row_number)
        ).all()
        self.assertEqual(rows, [(2, "2025-1", 1), (3, "2026-1", 2), (4, "2025-1", 1)])
        self.assertEqual(response.filters.periods, ["2025-1", "2026-1"])
        self.assertEqual(response.filters.moments, [1, 2])
        self.assertEqual(
            response.source_audit.data_quality.period_moment.rows_without_period, 0
        )

    def test_filters_by_period_and_moment(self) -> None:
        response = self._import()

        moment_two = self.service.get_overview(
            self.db, response.import_id, DashboardFilterQuery(moment=2), 1, 50
        )
        self.assertEqual(moment_two.kpis.presentations, 1)
        self.assertEqual(moment_two.selected_filters.moment, 2)
        period = self.service.get_overview(
            self.db,
            response.import_id,
            DashboardFilterQuery(period="2025-1"),
            1,
            50,
        )
        self.assertEqual(period.kpis.presentations, 1)
        self.assertEqual(period.kpis.not_presented_records, 1)

    def test_student_history_shows_moment_and_semester_range(self) -> None:
        response = self._import()

        student = self.service.get_student(self.db, response.import_id, "101")

        self.assertEqual(
            [
                (attempt.period, attempt.moment, attempt.semester_range)
                for attempt in student.history
            ],
            [("2025-1", 1, "1–3"), ("2026-1", 2, "4–6")],
        )

    def test_new_ese_import_does_not_replace_corhuila(self) -> None:
        corhuila_id = self._seed_corhuila("2026-2")
        first = self._import()
        second = self._import(global_score=91)

        statuses = dict(
            self.db.execute(select(ExcelImport.id, ExcelImport.status)).all()
        )
        self.assertEqual(statuses[first.import_id], "HISTORICAL")
        self.assertEqual(statuses[second.import_id], "ACTIVE")
        self.assertEqual(statuses[corhuila_id], "ACTIVE")

        imports = self.service.list_admin_imports(self.db, 100)
        self.assertEqual(imports.active_import_id, second.import_id)
        self.assertEqual(
            [(item.slot, item.import_id) for item in imports.active_imports],
            [("CORHUILA:2026-2", corhuila_id), ("ESE", second.import_id)],
        )
        self.assertEqual(
            {item.import_id: item.source for item in imports.imports}[corhuila_id],
            "CORHUILA",
        )
        self.assertEqual(
            self.service.get_active_import(self.db, "ESE").import_id,
            second.import_id,
        )

    def test_deleting_ese_active_keeps_corhuila_active(self) -> None:
        corhuila_id = self._seed_corhuila("2026-2")
        ese = self._import()

        self.service.delete_import(self.db, ese.import_id)

        slots = list(self.db.scalars(select(ActiveImport.slot)))
        self.assertEqual(slots, ["CORHUILA:2026-2"])
        with self.assertRaises(ApplicationError) as error:
            self.service.get_active_import(self.db, "ESE")
        self.assertEqual(error.exception.status_code, 404)
        self.assertEqual(
            self.db.get(ExcelImport, corhuila_id).status, "ACTIVE"
        )


if __name__ == "__main__":
    unittest.main()
