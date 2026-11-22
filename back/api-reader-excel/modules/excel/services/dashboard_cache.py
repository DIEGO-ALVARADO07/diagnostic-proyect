"""Caché en memoria de los datasets del dashboard, por importación.

Una importación ``ACTIVE`` o ``HISTORICAL`` es una instantánea que no cambia:
sus filas en ``academic_results`` y ``td_programas_reference`` solo se escriben
durante la importación. Por eso el dataset ya armado puede reutilizarse entre
peticiones sin volver a leer miles de filas de la base de datos.

La caché no decide si una importación es visible: el servicio siempre consulta
primero la fila de ``excel_imports`` (estado y ``deleted_at``). Así, aunque haya
varios procesos de Uvicorn con cachés independientes, una importación
desactivada deja de servirse en todos ellos.
"""

from collections import OrderedDict
from threading import Lock

from modules.excel.entities.dashboard import DashboardDataset

# Importación activa + un par de históricas consultadas por el superadmin.
DEFAULT_MAX_ENTRIES = 3


class DashboardDatasetCache:
    """LRU acotada y segura entre hilos (las rutas corren en un threadpool)."""

    def __init__(self, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        if max_entries < 0:
            raise ValueError("max_entries no puede ser negativo.")
        self._max_entries = max_entries
        self._entries: OrderedDict[str, DashboardDataset] = OrderedDict()
        self._lock = Lock()

    @property
    def max_entries(self) -> int:
        return self._max_entries

    def get(self, import_id: str) -> DashboardDataset | None:
        with self._lock:
            dataset = self._entries.get(import_id)
            if dataset is not None:
                self._entries.move_to_end(import_id)
            return dataset

    def put(self, dataset: DashboardDataset) -> None:
        if self._max_entries == 0:
            return
        with self._lock:
            self._entries[dataset.import_id] = dataset
            self._entries.move_to_end(dataset.import_id)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)

    def invalidate(self, import_id: str) -> None:
        with self._lock:
            self._entries.pop(import_id, None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __contains__(self, import_id: object) -> bool:
        with self._lock:
            return import_id in self._entries

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
