import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

db_driver = os.getenv("ALEMBIC_DB_DRIVER")
db_host = os.getenv("ALEMBIC_DB_HOST")
db_port = os.getenv("ALEMBIC_DB_PORT")
db_username = os.getenv("ALEMBIC_DB_USERNAME")
db_database = os.getenv("ALEMBIC_DB_DATABASE")

db_password = None
pass_path = os.getenv("ALEMBIC_DB_PASSWORD_FILE")
if pass_path and os.path.exists(pass_path):
    db_password = open(pass_path).read().strip()
config.set_main_option(
    'sqlalchemy.url',
          f'{db_driver}://{db_username}:{db_password}@{db_host}:{db_port}/{db_database}'
)

target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata,
            version_table_schema="crm",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
