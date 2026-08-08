from neo4j import GraphDatabase

from app.core.config import settings

# One driver instance for the app's lifetime, same reasoning as main.py's
# health check driver: the Neo4j driver manages its own connection pool
# internally, so there's no need to open a new connection per operation.
driver = GraphDatabase.driver(
    settings.neo4j_uri,
    auth=(settings.neo4j_user, settings.neo4j_password),
)