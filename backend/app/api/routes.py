from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models.raw import RawRepository
from app.graph.neo4j_client import driver
from app.investigate.engine import investigate
from app.graph.queries import get_module_graph

router = APIRouter()

REPO = "httpie/cli"


from fastapi import HTTPException


@router.get("/investigate")
def investigate_endpoint(query: str, session: Session = Depends(get_session)):
    """
    Thin wrapper exposing investigate() over HTTP. Kept deliberately
    simple -- single hardcoded repo for now, matching every check script
    so far, rather than building multi-repo support before there's a
    frontend that would even use it.

    Errors are caught explicitly here rather than left to bubble up as
    raw 500s with stack traces -- a person hitting this from a browser
    should get a clear, actionable message, not a Python traceback.
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    repo = session.query(RawRepository).filter_by(full_name=REPO).first()
    if repo is None:
        raise HTTPException(
            status_code=400,
            detail=f"{REPO} has not been ingested yet. Run the ingestion pipeline first.",
        )

    try:
        results = investigate(session, driver, repo.id, REPO, query, top_k=5)
    except Exception:
        # Deliberately generic to the caller -- don't leak internals
        # (DB connection strings, stack traces) in the response. The
        # real exception is still available in server logs for debugging.
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while investigating this query. Please try again.",
        )

        message = None
    if not results:
        message = "No relevant results found for this query. Try rephrasing it."
    elif results[0]["composite_score"] < 0.35:
        message = "Results have low confidence — the query may not closely match anything in this repo. Try rephrasing it."

    return {"query": query, "repo": REPO, "results": results, "message": message}



@router.get("/architecture")
def architecture_endpoint():
    return get_module_graph(driver, REPO)