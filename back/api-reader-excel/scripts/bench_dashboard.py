"""Benchmark del dashboard: importa un libro sintético y mide consultas repetidas.

Usa SQLite en memoria; no necesita core/.env ni MySQL. Con MySQL real, la
lectura sin caché es más lenta por la latencia de red.

Uso (desde la raíz del backend, PowerShell):
    $env:PYTHONPATH = "."; venv\\Scripts\\python.exe scripts\\bench_dashboard.py 20000
"""

import io
import random
import sys
import zipfile
from time import perf_counter
from xml.sax.saxutils import escape

import logging

logging.disable(logging.WARNING)

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from modules.excel.dtos.requests.dashboard import DashboardFilterQuery
from modules.excel.dtos.requests.read_workbook import ReadWorkbookRequest
from modules.excel.entities.academic import DashboardState
from modules.excel.services.dashboard_service import DashboardService
from modules.security.entities import Account, AuthBase
from modules.security.entities.role import Role
from tests.test_dashboard import BD_HEADERS, _sheet_xml

ROWS = int(sys.argv[1]) if len(sys.argv) > 1 else 20_000
REPEAT = 5
random.seed(7)


def build_workbook(rows: int) -> bytes:
    programs = [f"PROGRAMA {index:02d}" for index in range(30)]
    sims = ["SIMULACRO 2025-1 MOMENTO 1", "SIMULACRO 2025-2 MOMENTO 2"]
    bd = [BD_HEADERS]
    for index in range(rows):
        scores = [random.randint(80, 250) for _ in range(5)]
        bd.append(
            [
                str(1000 + index // 2), "Nombre", f"Apellido {index}",
                f"user{index}@example.com", *scores, sum(scores) / 5,
                programs[index % len(programs)], None, "SABER PRO",
                f"SEMESTRE {index % 10}", 2025, sims[index % 2],
                None, None, None, None, None, None, f"G{index % 5}",
                "Si" if index % 7 else "No", None, None,
            ]
        )
    td = [
        # fastexcel toma la primera fila como encabezado: se añade una fila de título.
        ["TD", "LC", "CE", "CC", "RC", "I", "GL", "GL"],
        ["AÑO", 2025, None, None, None, None, None, None],
        ["PROGRAMA", "LC", "CE", "CC", "RC", "I", "GL", "GL"],
        [sims[0], None, None, None, None, None, None, None],
        *[[name, 150, 150, 150, 150, 150, 150, 150] for name in programs],
    ]
    sheets = [("BD GEN", bd), ("TD PROGRAMAS", td)]
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    ct = "application/vnd.openxmlformats-officedocument.spreadsheetml"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f'<Override PartName="/xl/workbook.xml" ContentType="{ct}.sheet.main+xml"/>'
            + "".join(
                f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="{ct}.worksheet+xml"/>'
                for i in range(1, len(sheets) + 1)
            )
            + "</Types>",
        )
        archive.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{rel}/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        archive.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{main}" xmlns:r="{rel}"><sheets>'
            + "".join(
                f'<sheet name="{escape(n)}" sheetId="{i}" r:id="rId{i}"/>'
                for i, (n, _) in enumerate(sheets, start=1)
            )
            + "</sheets></workbook>",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(
                f'<Relationship Id="rId{i}" Type="{rel}/worksheet" Target="worksheets/sheet{i}.xml"/>'
                for i in range(1, len(sheets) + 1)
            )
            + "</Relationships>",
        )
        for i, (_, rows_) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{i}.xml", _sheet_xml(rows_))
    return buffer.getvalue()


def timed(label: str, func) -> None:
    samples = []
    for _ in range(REPEAT):
        started = perf_counter()
        func()
        samples.append(perf_counter() - started)
    print(
        f"{label:<28} primera={samples[0]*1000:8.1f} ms   "
        f"siguientes(media)={sum(samples[1:])/(len(samples)-1)*1000:8.1f} ms"
    )


def main() -> None:
    engine = create_engine("sqlite://")
    AuthBase.metadata.create_all(engine)
    db = Session(engine)
    account = Account(
        id=1, username="bench", email="b@example.com", full_name="Bench",
        password_hash="x", role=Role.SUPERADMIN.value, is_active=True,
    )
    db.add_all([account, DashboardState(id=1)])
    db.commit()

    service = DashboardService()
    started = perf_counter()
    response = service.import_workbook(
        ReadWorkbookRequest(filename="bench.xlsx", content=build_workbook(ROWS)),
        account, db,
    )
    print(f"filas={ROWS}  importación={perf_counter()-started:.2f} s")
    import_id = response.import_id
    program_id = response.filters.programs[0].program_id

    timed("overview sin filtros", lambda: service.get_overview(
        db, import_id, DashboardFilterQuery(), 1, 50, account))
    timed("overview filtrado", lambda: service.get_overview(
        db, import_id, DashboardFilterQuery(group="G1"), 1, 50, account))
    timed("programa", lambda: service.get_program(
        db, import_id, program_id, DashboardFilterQuery(), None, 1, 50, account))
    timed("estudiante", lambda: service.get_student(
        db, import_id, "1500", account))


if __name__ == "__main__":
    main()
