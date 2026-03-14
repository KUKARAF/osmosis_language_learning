from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import event

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.close()


async def init_db():
    """Create tables from ORM metadata (used in dev/testing; prod uses alembic)."""
    from app.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)


def _add_missing_columns(conn):
    """ADD COLUMN for any columns that create_all doesn't handle on existing tables."""
    _additions = [
        ("conversations", "summary", "TEXT"),
        ("conversations", "summary_through_msg_id", "TEXT"),
    ]
    for table, column, col_type in _additions:
        try:
            conn.execute(
                __import__("sqlalchemy").text(
                    f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
                )
            )
        except Exception:
            pass  # column already exists


async def get_db():
    async with async_session() as session:
        yield session
