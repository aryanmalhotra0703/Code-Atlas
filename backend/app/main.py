from fastapi import FastAPI
from sqlalchemy import create_engine, text
from neo4j import GraphDatabase

from app.core.config import settings

app = FastAPI(title="Code Atlas API")

# create_engine() doesn't actually connect yet — SQLAlchemy connects lazily,
# on first query. That's why /health below runs a real query rather than
# just checking that this line didn't crash.
postgres_engine = create_engine(settings.postgres_url)

# The Neo4j driver is similar: creating it just prepares connection info.
# We keep one driver instance for the app's lifetime rather than opening
# a new connection per request — connections are pooled internally.
neo4j_driver = GraphDatabase.driver(
    settings.neo4j_uri,
    auth=(settings.neo4j_user, settings.neo4j_password),
)


@app.get("/health")
def health_check():
    """
    Confirms the API can actually talk to both databases, not just that
    the FastAPI process is alive. A /health that only returns {"ok": true}
    without touching dependencies will happily report healthy while
    Postgres or Neo4j are unreachable — exactly the failure mode you
    don't want to discover during a live demo.
    """
    status = {"api": "ok", "postgres": "unknown", "neo4j": "unknown"}

    try:
        with postgres_engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
        status["postgres"] = "ok"
        status["postgres_version"] = version
    except Exception as e:
        status["postgres"] = f"error: {e}"

    try:
        neo4j_driver.verify_connectivity()
        status["neo4j"] = "ok"
    except Exception as e:
        status["neo4j"] = f"error: {e}"

    return status
