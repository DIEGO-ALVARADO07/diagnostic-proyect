from pathlib import Path

from alembic.config import Config

from core.database import engine
from migrations.runner import DatabaseMigrationService


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    migration_config = Config(str(project_root / "alembic.ini"))
    DatabaseMigrationService(migration_config, engine).upgrade()


if __name__ == "__main__":
    main()
