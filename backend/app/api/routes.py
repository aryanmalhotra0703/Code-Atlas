from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.db.session import get_session
from app.models.raw import RawRepository
from app.graph.neo4j_client import driver
from app.investigate.engine import investigate
from app.graph.queries import get_module_graph

logger = logging.getLogger(__name__)

router = APIRouter()

REPO = "httpie/cli"


@router.get("/investigate")
def investigate_endpoint(query: str, session: Session = Depends(get_session)):
    """
    Thin wrapper exposing investigate() over HTTP.

    Errors are caught explicitly here rather than left to bubble up as
    raw 500s with stack traces -- a person hitting this from a browser
    should get a clear, actionable message, not a Python traceback.
    The real exception is always logged server-side for debugging via
    Render's log tail.
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
    except Exception as exc:
        # Log the real exception so it appears in Render's log tail for
        # debugging, without leaking stack traces or internals to API callers.
        logger.exception("investigate() failed for query %r: %s", query, exc)
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while investigating this query. Please try again.",
        )

    # NOTE: message = None must live here, outside the try/except, not inside
    # the except block. Previously it was accidentally placed after a `raise`
    # inside the except, making it unreachable on the success path and causing
    # an UnboundLocalError crash on any query that returned good results.
    message = None
    if not results:
        message = "No relevant results found for this query. Try rephrasing it."
    elif results[0]["composite_score"] < 0.35:
        message = "Results have low confidence — the query may not closely match anything in this repo. Try rephrasing it."

    return {"query": query, "repo": REPO, "results": results, "message": message}


@router.get("/architecture")
def architecture_endpoint():
    return get_module_graph(driver, REPO)