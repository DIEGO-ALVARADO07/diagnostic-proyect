import unittest
from types import MappingProxyType
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from core.exceptions import ApplicationError
from modules.excel.dtos.requests.dashboard import DashboardFilterQuery
from modules.excel.dtos.requests.read_workbook import ReadWorkbookRequest
from modules.excel.entities.academic import DashboardState
from modules.excel.entities.dashboard import DashboardDataset
from modules.excel.services.dashboard_cache import DashboardDatasetCache
from modules.excel.services.dashboard_service import DashboardService
from modules.security.entities import Account, AuthBase
from modules.security.entities.role import Role
from tests.test_dashboard import make_dashboard_workbook


def _dataset(import_id: str) -> DashboardDataset:
    return DashboardDataset(
        import_id=import_id,
        filename=f"{import_id}.xlsx",
        records=(),
        records_by_program=MappingProxyType({}),
        records_by_student=MappingProxyType({}),
        program_names=MappingProxyType({}),
        td_programs_year=None,
        td_programs_summary=MappingProxyType({}),
        records_without_document=0,
    )


class DashboardDatasetCacheTests(unittest.TestCase):
    def test_returns_none_when_missing(self) -> None:
        self.assertIsNone(DashboardDatasetCache().get("missing"))

    def test_evicts_least_recently_used(self) -> None:
        cache = DashboardDatasetCache(max_entries=2)
        cache.put(_dataset("a"))
        cache.put(_dataset("b"))
        cache.get("a")  # "a" pasa a ser el más reciente
        cache.put(_dataset("c"))

        self.assertIn("a", cache)
        self.assertNotIn("b", cache)
        self.assertIn("c", cache)
        self.assertEqual(len(cache), 2)

    def test_invalidate_and_clear(self) -> None:
        cache = DashboardDatasetCache()
        cache.put(_dataset("a"))
        cache.put(_dataset("b"))

        cache.invalidate("a")
        cache.invalidate("unknown")
        self.assertNotIn("a", cache)
        self.assertIn("b", cache)

        cache.clear()
        self.assertEqual(len(cache), 0)

    def test_zero_entries_disables_cache(self) -> None:
        cache = DashboardDatasetCache(max_entries=0)
        cache.put(_dataset("a"))
        self.assertIsNone(cache.get("a"))

    def test_rejects_negative_size(self) -> None:
        with self.assertRaises(ValueError):
            DashboardDatasetCache(max_entries=-1)


class DashboardServiceCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        AuthBase.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.superadmin = Account(
            id=1,
            username="admin",
            email="admin@example.com",
            full_name="Admin",
            password_hash="unused",
            role=Role.SUPERADMIN.value,
            is_active=True,
        )
        self.db.add_all([self.superadmin, DashboardState(id=1)])
        self.db.commit()
        self.cache = DashboardDatasetCache()
        self.service = DashboardService(dataset_cache=self.cache)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def _import(self, global_score: object = 90) -> str:
        response = self.service.import_workbook(
            ReadWorkbookRequest(
                filename="results.xlsx",
                content=make_dashboard_workbook(global_score),
            ),
            self.superadmin,
            self.db,
        )
        return response.import_id

    def _overview(self, import_id: str):
        return self.service.get_overview(
            self.db,
            import_id,
            DashboardFilterQuery(),
            page=1,
            page_size=50,
            account=self.superadmin,
        )

    def test_import_primes_cache_and_queries_reuse_it(self) -> None:
        import_id = self._import()
        self.assertIn(import_id, self.cache)

        with patch.object(
            DashboardService,
            "_load_dataset",
            wraps=DashboardService._load_dataset,
        ) as load_dataset:
            first = self._overview(import_id)
            second = self._overview(import_id)
            self.service.get_student(
                self.db, import_id, "101", account=self.superadmin
            )

        load_dataset.assert_not_called()
        self.assertEqual(first, second)

    def test_cache_miss_loads_once_then_hits(self) -> None:
        import_id = self._import()
        self.cache.clear()

        with patch.object(
            DashboardService,
            "_load_dataset",
            wraps=DashboardService._load_dataset,
        ) as load_dataset:
            uncached = self._overview(import_id)
            cached = self._overview(import_id)

        self.assertEqual(load_dataset.call_count, 1)
        self.assertEqual(uncached, cached)

    def test_deleted_import_is_evicted_and_not_served(self) -> None:
        import_id = self._import()
        self.assertIn(import_id, self.cache)

        self.service.delete_import(self.db, import_id)

        self.assertNotIn(import_id, self.cache)
        with self.assertRaises(ApplicationError) as context:
            self._overview(import_id)
        self.assertEqual(context.exception.status_code, 404)

    def test_deleted_import_not_served_even_if_still_cached(self) -> None:
        # Simula otro proceso de Uvicorn cuya caché no se invalidó.
        import_id = self._import()
        stale_cache = DashboardDatasetCache()
        stale_cache.put(self.cache.get(import_id))
        other_worker = DashboardService(dataset_cache=stale_cache)

        self.service.delete_import(self.db, import_id)

        self.assertIn(import_id, stale_cache)
        with self.assertRaises(ApplicationError) as context:
            other_worker.get_overview(
                self.db,
                import_id,
                DashboardFilterQuery(),
                page=1,
                page_size=50,
                account=self.superadmin,
            )
        self.assertEqual(context.exception.status_code, 404)

    def test_cached_dataset_is_read_only(self) -> None:
        dataset = self.cache.get(self._import())

        self.assertIsInstance(dataset.records, tuple)
        with self.assertRaises(TypeError):
            dataset.records_by_program["new"] = ()  # type: ignore[index]
        with self.assertRaises(TypeError):
            dataset.program_names["new"] = "x"  # type: ignore[index]
        for records in dataset.records_by_program.values():
            self.assertIsInstance(records, tuple)


if __name__ == "__main__":
    unittest.main()
