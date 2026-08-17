from sentence_transformers import SentenceTransformer
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.raw import RawCommit, RawPullRequest
from app.models.embedding import Embedding

MODEL_NAME = "all-MiniLM-L6-v2"
BATCH_SIZE = 100

# Loaded once at import time, not inside a function -- loading the model
# (downloading weights on first run, then loading into memory) is the
# slow part, so we don't want to repeat that on every call.
_model = SentenceTransformer(MODEL_NAME)


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Runs the embedding model locally -- no network call, no API key,
    no cost. Returns one vector per input text, same order they came in.
    """
    vectors = _model.encode(texts, show_progress_bar=False)
    return vectors.tolist()


def embed_repo(session: Session, repo_id: int) -> int:
    """
    Embeds every commit message and PR (title + body) for this repo that
    hasn't already been embedded, storing results in the embeddings
    table. Idempotent via ON CONFLICT DO NOTHING on (repo_id, source_type,
    source_id).

    Returns the number of new embeddings actually stored.
    """
    commits = session.query(RawCommit).filter_by(repo_id=repo_id).all()
    prs = session.query(RawPullRequest).filter_by(repo_id=repo_id).all()

    items: list[tuple[str, str, str]] = []
    for c in commits:
        items.append(("commit", c.sha, c.message or ""))
    for pr in prs:
        content = f"{pr.title or ''}\n\n{pr.body or ''}".strip()
        items.append(("pull_request", str(pr.number), content))

    stored = 0
    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i:i + BATCH_SIZE]
        texts = [content for _, _, content in batch]
        vectors = get_embeddings(texts)

        for (source_type, source_id, content), vector in zip(batch, vectors):
            stmt = (
                pg_insert(Embedding)
                .values(
                    repo_id=repo_id,
                    source_type=source_type,
                    source_id=source_id,
                    content=content,
                    embedding=vector,
                )
                .on_conflict_do_nothing(index_elements=["repo_id", "source_type", "source_id"])
            )
            result = session.execute(stmt)
            stored += result.rowcount

        session.commit()

    return stored