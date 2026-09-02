from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import re
from sqlalchemy import create_engine, text
from neo4j import GraphDatabase

from app.core.config import settings
from app.api.routes import router

app = FastAPI(title="Code Atlas API")

# Temporary startup diagnostic: prints which Postgres host and Neo4j URI
# this running instance is actually connecting to (host only for
# Postgres, no credentials), so we can definitively compare it against
# what we expect instead of guessing from a manual copy-paste comparison.
_host_match = re.search(r"@([^/]+)/", settings.postgres_url)
print(f"[STARTUP] Connecting to Postgres host: {_host_match.group(1) if _host_match else 'UNKNOWN'}")
print(f"[STARTUP] Connecting to Neo4j URI: {settings.neo4j_uri}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

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
    the FastAPI process is alive.
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