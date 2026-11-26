"""Copia de seguridad de la base MySQL con ``mysqldump``.

Uso (desde ``tasks.ps1 backup`` y ``tasks.ps1 backup-daily``)::

    python -m scripts.backup_db [--output-dir CARPETA] [--label antes-0008]
    python -m scripts.backup_db --if-changed --label diario [--keep 30]

- Lee las credenciales de ``core/.env`` (descifra las de Fernet con
  ``APP_MASTER_KEY``) y las pasa a ``mysqldump`` en un archivo temporal de
  opciones, no en la línea de comandos, y lo borra al terminar.
- Busca ``mysqldump`` en el PATH o en ``C:\\laragon\\bin\\mysql\\*\\bin``.
- El respaldo incluye ``DROP DATABASE`` + ``CREATE DATABASE``: al restaurarlo,
  la base vuelve exactamente al estado de la copia.
- Por defecto se guarda en ``%USERPROFILE%\\respaldos\\<base>``, fuera del
  repositorio: contiene datos personales y nunca debe ir a Git.
- ``--if-changed`` (respaldo diario): antes de copiar calcula una huella de
  los datos (``CHECKSUM TABLE`` de cada tabla) y la compara con la del último
  respaldo, guardada en ``.ultimo-respaldo.json`` de la misma carpeta. Si no
  cambió nada, no crea otro archivo. Las sesiones (``api_access_tokens``) no
  cuentan: iniciar sesión no es un cambio de datos.
- ``--keep N`` (opcional): conserva solo los N respaldos más recientes con la
  misma etiqueta; los de otras etiquetas (``antes-0008``…) no se tocan.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

LARAGON_MYSQL = Path("C:/laragon/bin/mysql")
STATE_FILE = ".ultimo-respaldo.json"
IGNORED_TABLES = frozenset({"api_access_tokens"})
"""Tablas que cambian sin que cambien los datos (sesiones)."""


def find_mysqldump(explicit: str | None = None) -> Path:
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return path
        raise FileNotFoundError(f"No existe mysqldump en {path}.")
    found = shutil.which("mysqldump")
    if found:
        return Path(found)
    candidates = sorted(LARAGON_MYSQL.glob("*/bin/mysqldump.exe"), reverse=True)
    if candidates:
        return candidates[0]
    raise FileNotFoundError(
        "No se encontró mysqldump. Indica la ruta con -MysqlDump "
        "(por ejemplo C:\\laragon\\bin\\mysql\\mysql-8.4.3-winx64\\bin\\mysqldump.exe)."
    )


def backup_path(output_dir: Path, database: str, label: str | None, now: datetime) -> Path:
    stamp = now.strftime("%Y-%m-%d_%H%M")
    suffix = f"_{label}" if label else ""
    return output_dir / f"{database}_{stamp}{suffix}.sql"


def options_file_content(user: str, password: str, host: str, port: int) -> str:
    def quote(value: str) -> str:
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'

    return (
        "[client]\n"
        f"user={quote(user)}\n"
        f"password={quote(password)}\n"
        f"host={quote(host)}\n"
        f"port={port}\n"
    )


def dump_command(
    mysqldump: Path, options_file: Path, database: str, output: Path
) -> list[str]:
    # --defaults-extra-file debe ser la primera opción.
    return [
        str(mysqldump),
        f"--defaults-extra-file={options_file}",
        "--single-transaction",
        "--routines",
        "--triggers",
        "--add-drop-database",
        "--default-character-set=utf8mb4",
        f"--result-file={output}",
        "--databases",
        database,
    ]


def fingerprint(checksums: Iterable[tuple[str, object]]) -> str:
    """Huella de los datos a partir del ``CHECKSUM TABLE`` de cada tabla."""
    rows = sorted(
        (str(table).split(".")[-1], "" if value is None else str(value))
        for table, value in checksums
        if str(table).split(".")[-1] not in IGNORED_TABLES
    )
    return hashlib.sha256(json.dumps(rows).encode("utf-8")).hexdigest()


def database_fingerprint() -> str:
    """Huella de la base configurada (solo lectura)."""
    from sqlalchemy import text

    from core.database import engine

    with engine.connect() as connection:
        tables = [row[0] for row in connection.execute(text("SHOW TABLES"))]
        if not tables:
            return fingerprint([])
        quoted = ", ".join(f"`{table}`" for table in tables)
        checksums = connection.execute(text(f"CHECKSUM TABLE {quoted}")).all()
    return fingerprint((row[0], row[1]) for row in checksums)


def read_state(output_dir: Path) -> dict:
    try:
        return json.loads((output_dir / STATE_FILE).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def write_state(output_dir: Path, value: str, backup: Path, now: datetime) -> None:
    (output_dir / STATE_FILE).write_text(
        json.dumps(
            {"fingerprint": value, "file": backup.name, "created_at": now.isoformat()},
            indent=2,
        ),
        encoding="utf-8",
    )


def prune(output_dir: Path, database: str, label: str, keep: int) -> list[Path]:
    """Borra los respaldos más viejos con ``label``; deja los ``keep`` más recientes."""
    if keep < 1:
        return []
    backups = sorted(
        output_dir.glob(f"{database}_*_{label}.sql"),
        key=lambda path: path.name,
        reverse=True,
    )
    removed = backups[keep:]
    for path in removed:
        path.unlink()
    return removed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir")
    parser.add_argument("--label")
    parser.add_argument("--mysqldump")
    parser.add_argument(
        "--if-changed",
        action="store_true",
        help="No crea la copia si los datos no cambiaron desde la última.",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=0,
        help="Conserva solo los N respaldos más recientes con la misma etiqueta.",
    )
    args = parser.parse_args(argv)

    from core.config import settings  # Carga y descifra core/.env.

    output_dir = Path(
        args.output_dir
        or Path.home() / "respaldos" / settings.DB_NAME
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    current = database_fingerprint()
    if args.if_changed:
        state = read_state(output_dir)
        last_file = state.get("file")
        if state.get("fingerprint") == current and last_file and (output_dir / last_file).exists():
            print(
                f"Sin cambios desde el último respaldo ({last_file}); "
                "no se creó otra copia."
            )
            return 0
    output = backup_path(output_dir, settings.DB_NAME, args.label, now)
    mysqldump = find_mysqldump(args.mysqldump)

    descriptor, options_name = tempfile.mkstemp(suffix=".cnf")
    options_file = Path(options_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(
                options_file_content(
                    settings.DB_USER,
                    settings.DB_PASSWORD,
                    settings.DB_HOST,
                    settings.DB_PORT,
                )
            )
        completed = subprocess.run(
            dump_command(mysqldump, options_file, settings.DB_NAME, output),
            check=False,
        )
    finally:
        options_file.unlink(missing_ok=True)

    if completed.returncode != 0 or not output.exists():
        print("La copia de seguridad falló.", file=sys.stderr)
        return completed.returncode or 1
    size_mib = output.stat().st_size / (1024 * 1024)
    print(f"Copia de seguridad creada: {output} ({size_mib:.1f} MiB)")
    # Toda copia (manual o diaria) actualiza la huella: la diaria compara
    # contra la última copia que exista, sea cual sea su etiqueta.
    write_state(output_dir, current, output, now)
    if args.label and args.keep:
        for path in prune(output_dir, settings.DB_NAME, args.label, args.keep):
            print(f"Respaldo antiguo eliminado: {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
