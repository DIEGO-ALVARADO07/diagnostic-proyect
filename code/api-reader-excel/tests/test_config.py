import os
import unittest
from unittest.mock import patch

with patch.dict(
    os.environ,
    {
        "DB_USER": "settings_test_user",
        "DB_PASSWORD": "settings_test_password",
        "DB_HOST": "localhost",
        "DB_PORT": "3306",
        "DB_NAME": "settings_test_database",
    },
):
    from core.config import Settings


class DatabaseSettingsTests(unittest.TestCase):
    def test_database_url_uses_configured_connection_values(self) -> None:
        settings = Settings(
            DB_USER="test_user",
            DB_PASSWORD="test_password",
            DB_HOST="localhost",
            DB_PORT=3306,
            DB_NAME="diagnostic",
        )

        self.assertEqual(
            settings.database_url,
            "mysql+pymysql://test_user:test_password@localhost:3306/diagnostic",
        )
