from pathlib import Path

from alembic.config import Config

from core.database import engine
from modules.security.services.migration_service import SecurityMigrationService


def main() -> None:
    project_root = Path(__file__).resolve().parents[3]
    migration_config = Config(str(project_root / "alembic.ini"))
    SecurityMigrationService(migration_config, engine).upgrade()


if __name__ == "__main__":
    main()
