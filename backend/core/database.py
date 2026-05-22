import logging

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.core.config import get_config

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


_engine = None
_SessionFactory = None


def get_engine():
    global _engine
    if _engine is None:
        config = get_config()
        _engine = create_engine(config.database.url, echo=config.database.echo)

        @event.listens_for(_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
            except Exception as exc:
                logger.warning("SQLite WAL mode unavailable, continuing with default journal mode: %s", exc)
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine())
    return _SessionFactory


def get_db():
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def init_db():
    import backend.models  # noqa: F401

    Base.metadata.create_all(get_engine())
