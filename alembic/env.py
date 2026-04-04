import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# ── make src/ importable ───────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

load_dotenv()

# CHANGED: import SYNC_DATABASE_URL instead of DATABASE_URL
from src.db.main import Base, SYNC_DATABASE_URL
from src.db.models import (
    School,
    User,
    Class,
    ClassTeacher,
    Enrollment,
    Book,
    ClassChapter,
    Quiz,
    TeacherProfile,
)

config = context.config

config.set_main_option("sqlalchemy.url", SYNC_DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
