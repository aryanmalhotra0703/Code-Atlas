from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """
    Every ORM model (RawRepository, RawCommit, etc.) inherits from this.
    Alembic reads Base.metadata to know what tables *should* exist, and
    compares that against what actually exists in Postgres to figure out
    what migrations to generate — this class is the link between your
    Python model definitions and the database schema.
    """
    pass


engine = create_engine(
    settings.postgres_url,
    pool_pre_ping=True,   # tests each connection with a lightweight query
                           # before handing it out, so a connection Neon
                           # silently closed in the background gets
                           # detected and replaced instead of causing a
                           # confusing mid-request failure
    pool_recycle=280,     # proactively discards and replaces connections
                           # older than ~4.5 minutes, staying safely under
                           # Neon's own idle-connection timeout
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session():
    """
    Yields a session and guarantees it's closed afterward, even if an
    error happens mid-use. This is the standard FastAPI dependency pattern —
    routes will later use this via Depends(get_session) to get a session
    scoped to just that one request.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()