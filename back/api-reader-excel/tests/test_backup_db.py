import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from scripts.backup_db import (
    backup_path,
    dump_command,
    find_mysqldump,
    options_file_content,
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


if __name__ == "__main__":
    unittest.main()
