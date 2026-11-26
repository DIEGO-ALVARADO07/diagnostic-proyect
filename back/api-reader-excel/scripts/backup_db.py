"""Copia de seguridad de la base MySQL con ``mysqldump``.

Uso (desde ``tasks.ps1 backup``)::

    python -m scripts.backup_db [--output-dir CARPETA] [--label antes-0008]

- Lee las credenciales de ``core/.env`` (descifra las de Fernet con
  ``APP_MASTER_KEY``) y las pasa a ``mysqldump`` en un archivo temporal de
  opciones, no en la línea de comandos, y lo borra al terminar.
- Busca ``mysqldump`` en el PATH o en ``C:\\laragon\\bin\\mysql\\*\\bin``.
- El respaldo incluye ``DROP DATABASE`` + ``CREATE DATABASE``: al restaurarlo,
  la base vuelve exactamente al estado de la copia.
- Por defecto se guarda en ``%USERPROFILE%\\respaldos\\<base>``, fuera del
  repositorio: contiene datos personales y nunca debe ir a Git.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

LARAGON_MYSQL = Path("C:/laragon/bin/mysql")


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir")
    parser.add_argument("--label")
    parser.add_argument("--mysqldump")
    args = parser.parse_args(argv)

    from core.config import settings  # Carga y descifra core/.env.

    output_dir = Path(
        args.output_dir
        or Path.home() / "respaldos" / settings.DB_NAME
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output = backup_path(output_dir, settings.DB_NAME, args.label, datetime.now())
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
