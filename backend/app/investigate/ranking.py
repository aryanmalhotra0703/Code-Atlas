import math
from datetime import datetime, timezone

SIMILARITY_WEIGHT = 0.5
RECENCY_WEIGHT = 0.3
BLAST_RADIUS_WEIGHT = 0.2

RECENCY_HALF_LIFE_DAYS = 180  # after ~6 months, recency contributes half its original weight


def recency_score(date: datetime | None, now: datetime | None = None) -> float:
    """
    Converts a date into a 0-1 freshness score using exponential decay:
    a change from today scores close to 1, a change from a year ago
    scores meaningfully lower, but never hits exactly 0 -- old changes
    still count for something, just less.
    """
    if date is None:
        return 0.0
    now = now or datetime.now(timezone.utc)
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    days = max((now - date).total_seconds() / 86400, 0)
    return math.exp(-days / RECENCY_HALF_LIFE_DAYS)


def blast_radius_score(total_blast_radius: int) -> float:
    """
    Log-scaled so a file with 54 dependents doesn't completely dominate
    one with 5 -- the *relative* difference between "central" and
    "peripheral" code matters more than the raw count once it's large.
    Capped near 1.0 around ~100 files, past which more doesn't
    meaningfully change how central something is.
    """
    if total_blast_radius <= 0:
        return 0.0
    return min(math.log1p(total_blast_radius) / math.log1p(100), 1.0)


def composite_score(similarity: float, date: datetime | None, total_blast_radius: int) -> float:
    """
    Combines three independent signals into one explainable ranking
    score, instead of relying on embedding similarity alone:
      - similarity: does the text actually relate to the query?
      - recency: was this touched recently, or long settled?
      - blast radius: how structurally central is the affected code?

    Weights (0.5 / 0.3 / 0.2) are a deliberate design choice, not a
    tuned optimum: semantic relevance should dominate -- a highly
    similar old, peripheral commit should still usually outrank a
    barely-similar recent, central one -- while recency and structural
    importance still meaningfully shift the ranking rather than being
    ignored entirely.
    """
    return (
        SIMILARITY_WEIGHT * similarity
        + RECENCY_WEIGHT * recency_score(date)
        + BLAST_RADIUS_WEIGHT * blast_radius_score(total_blast_radius)
    )