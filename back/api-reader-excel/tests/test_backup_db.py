import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from scripts.backup_db import (
    backup_path,
    dump_command,
    find_mysqldump,
    fingerprint,
    options_file_content,
    prune,
    read_state,
    write_state,
)


class BackupDbTests(unittest.TestCase):
    def test_file_name_has_database_date_and_label(self) -> None:
        now = datetime(2026, 11, 26, 9, 5)
        self.assertEqual(
            backup_path(Path("C:/respaldos"), "excel_reader", "antes-0008", now).name,
            "excel_reader_2026-11-26_0905_antes-0008.sql",
        )
        self.assertEqual(
            backup_path(Path("C:/respaldos"), "excel_reader", None, now).name,
            "excel_reader_2026-11-26_0905.sql",
        )

    def test_credentials_go_to_an_options_file_not_the_command(self) -> None:
        content = options_file_content("root", 'cla"ve\\x', "127.0.0.1", 3306)
        self.assertIn('password="cla\\"ve\\\\x"', content)
        command = dump_command(
            Path("mysqldump"), Path("opts.cnf"), "excel_reader", Path("out.sql")
        )
        self.assertEqual(command[1], "--defaults-extra-file=opts.cnf")
        self.assertNotIn("root", " ".join(command))
        # Al restaurar, la base vuelve exactamente al estado de la copia.
        self.assertIn("--add-drop-database", command)
        self.assertEqual(command[-2:], ["--databases", "excel_reader"])

    def test_explicit_mysqldump_path_must_exist(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            tool = Path(folder) / "mysqldump.exe"
            tool.write_text("")
            self.assertEqual(find_mysqldump(str(tool)), tool)
            with self.assertRaises(FileNotFoundError):
                find_mysqldump(str(Path(folder) / "otro.exe"))

    def test_fingerprint_changes_only_with_data(self) -> None:
        base = [("excel_reader.courses", 10), ("excel_reader.api_users", 20)]
        same = fingerprint(base)
        # El orden de las tablas no importa.
        self.assertEqual(fingerprint(list(reversed(base))), same)
        # Iniciar sesión cambia api_access_tokens: no cuenta como cambio.
        self.assertEqual(fingerprint(base + [("excel_reader.api_access_tokens", 99)]), same)
        self.assertEqual(
            fingerprint(base + [("excel_reader.api_access_tokens", 5)]),
            fingerprint(base + [("excel_reader.api_access_tokens", 6)]),
        )
        # Editar un curso sí cambia la huella.
        self.assertNotEqual(
            fingerprint([("excel_reader.courses", 11), ("excel_reader.api_users", 20)]),
            same,
        )

    def test_state_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            self.assertEqual(read_state(output), {})
            backup = output / "excel_reader_2026-11-26_2200_diario.sql"
            write_state(output, "abc", backup, datetime(2026, 11, 26, 22, 0))
            state = read_state(output)
            self.assertEqual(state["fingerprint"], "abc")
            self.assertEqual(state["file"], backup.name)

    def test_prune_keeps_latest_daily_and_other_labels(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            names = [
                "excel_reader_2026-11-24_2200_diario.sql",
                "excel_reader_2026-11-25_2200_diario.sql",
                "excel_reader_2026-11-26_2200_diario.sql",
                "excel_reader_2026-11-20_0905_antes-0008.sql",
            ]
            for name in names:
                (output / name).write_text("")

            removed = prune(output, "excel_reader", "diario", keep=2)

            self.assertEqual([p.name for p in removed], [names[0]])
            left = sorted(p.name for p in output.iterdir())
            self.assertEqual(left, sorted(names[1:]))
            # keep=0 no borra nada.
            self.assertEqual(prune(output, "excel_reader", "diario", keep=0), [])


if __name__ == "__main__":
    unittest.main()
