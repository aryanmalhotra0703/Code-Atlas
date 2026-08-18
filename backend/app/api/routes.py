from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models.raw import RawRepository
from app.graph.neo4j_client import driver
from app.investigate.engine import investigate

router = APIRouter()

REPO = "httpie/cli"


@router.get("/investigate")
def investigate_endpoint(query: str, session: Session = Depends(get_session)):
    """
    Thin wrapper exposing investigate() over HTTP. Kept deliberately
    simple -- single hardcoded repo for now, matching every check script
    so far, rather than building multi-repo support before there's a
    frontend that would even use it.
    """
    repo = session.query(RawRepository).filter_by(full_name=REPO).first()
    if repo is None:
        return {"error": f"{REPO} has not been ingested yet"}

    results = investigate(session, driver, repo.id, REPO, query, top_k=5)
    return {"query": query, "repo": REPO, "results": results}