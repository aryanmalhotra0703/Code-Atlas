from sqlalchemy.orm import Session

from app.embeddings.pipeline import get_embeddings
from app.models.embedding import Embedding


def search(session: Session, repo_id: int, query_text: str, top_k: int = 5) -> list[dict]:
    """
    Embeds the query using the same local model used for ingestion --
    this matters, since query and stored embeddings must come from the
    same model, otherwise they'd be comparing incompatible vector spaces.

    Then finds the top_k closest stored embeddings by cosine distance.
    pgvector's <=> operator computes this directly inside Postgres, so
    the similarity search happens in the database, not in Python -- this
    scales far better than pulling every embedding into memory to
    compare manually.
    """
    query_vector = get_embeddings([query_text])[0]

    results = (
        session.query(
            Embedding.source_type,
            Embedding.source_id,
            Embedding.content,
            Embedding.embedding.cosine_distance(query_vector).label("distance"),
        )
        .filter(Embedding.repo_id == repo_id)
        .order_by("distance")
        .limit(top_k)
        .all()
    )

    return [
        {
            "source_type": r.source_type,
            "source_id": r.source_id,
            "content": r.content,
            "similarity": 1 - r.distance,  # 0-1 score, easier to read than raw distance
        }
        for r in results
    ]