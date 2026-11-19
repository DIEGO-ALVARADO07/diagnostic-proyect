from alembic import context

from core.database import engine
from modules.security.entities.base import AuthBase

target_metadata = AuthBase.metadata


def include_security_tables(
    name: str | None, object_type: str, parent_names: dict[str, str]
) -> bool:
    if object_type == "schema":
        return name is None
    if object_type == "table":
        return name in target_metadata.tables
    return parent_names.get("table_name") in target_metadata.tables


def run_migrations_offline() -> None:
    context.configure(
        url=str(engine.url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_name=include_security_tables,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_name=include_security_tables,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
