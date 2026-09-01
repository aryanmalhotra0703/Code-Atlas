# Code Atlas

A "detective" for codebases: describe a bug in plain English, and get a
ranked, explained trace to the real commits, PRs, files, owners, and
blast radius most likely responsible — built from a live GitHub repo,
not simulated data.

Demo repo: [`httpie/cli`](https://github.com/httpie/cli)

## The problem

At scale, finding "which file handles this, who owns it, and what
recently changed nearby" for an unfamiliar bug can take hours. Existing
tools either show you *structure* (dependency graphs, repo visualizers)
or let you *search text* (grep, GitHub's search) — nothing connects a
vague natural-language description of a problem to a concrete, explained
starting point.

## What it does

1. **Ingests** a real repo — metadata, commits, PRs — via the GitHub API,
   incrementally (only fetches what's new on repeat runs).
2. **Builds a graph** in Neo4j: files connected by real, AST-parsed
   import relationships; commits and PRs connected to the people and
   files they touched; ownership derived from edit frequency.
3. **Embeds** commit messages and PR text locally (no API cost), stored
   in Postgres via `pgvector`.
4. **On a query**, retrieves the most relevant commits/PRs by *meaning*
   (not keyword match), then walks the graph from each result to find
   real affected files, their derived owner, and their blast radius —
   fetching any missing graph detail on demand rather than depending on
   a fixed pre-load having covered it.

## Example

Query: *"SSL certificate verification is failing"*

Returns real, ranked PRs and commits about SSL certificate handling —
despite sharing almost no exact wording with the query — each traced to
the actual files they touched, who owns those files, and how many other
files depend on them. In this repo, the traversal automatically surfaced
that `httpie/compat.py` is the common thread across most SSL-related
fixes, with a blast radius of 54 files — a genuine architectural insight
found as a side effect of the search, not looked for directly.

## Architecture


- **FastAPI** — API layer
- **Postgres + pgvector** — structured data (repos, commits, PRs) and
  vector similarity search
- **Neo4j** — the graph itself (files, commits, people, and their
  relationships)
- **sentence-transformers** (`all-MiniLM-L6-v2`) — local embedding model
- **Docker Compose** — local orchestration

## Performance & scale

Tested against `httpie/cli` (133 files) throughout development, then
stress-tested against a genuinely larger repo, `django/django` (2,930
files, ~9,000 import edges), to find real bottlenecks rather than only
proving the happy path.

**Found:** the initial Neo4j graph-loading step took 83.5 seconds against
django — 89% of total pipeline runtime — caused by one network
round-trip per edge (a `MERGE` query in a loop).

**Fixed:** batched writes using Cypher's `UNWIND`, sending edges in
chunks of 1,000 per query instead of one query per edge. Same
idempotent logic, same correctness — just fewer, larger transactions.

**Result:** 83.5s → 26.7s, a 3.1x improvement, verified by re-running
the identical stress test before and after.

## Ranking

Results aren't ranked by raw embedding similarity alone. A composite
score combines three signals:

- **Similarity** (50%) — semantic relevance to the query
- **Recency** (30%) — exponentially decayed, so recent changes are
  weighted higher without completely ignoring older ones
- **Blast radius** (20%) — log-scaled structural centrality, so a
  result touching widely-depended-on code ranks higher than an
  equally-similar result touching an isolated file

Weights are a deliberate design choice, not a tuned optimum: semantic
relevance dominates, while recency and structural importance still
meaningfully shift rankings. See `backend/app/investigate/ranking.py`
for the implementation and reasoning.

## Known trade-offs

Stated explicitly rather than discovered later:

- Import resolution and ownership derivation are documented heuristics,
  not ground truth (see `NOTES.md` for full reasoning).
- The import graph currently only grows — deleted files/relationships
  upstream aren't reconciled.
- Graph data for commits/PRs outside the initial bounded batch loads
  lazily, on demand, at query time rather than being pre-warmed.
- Single-language (Python) import parsing.

Full build log, concept explanations, and design reasoning for every
decision live in `NOTES.md`.

## Running it

```bash
cp .env.example .env   # fill in GITHUB_TOKEN
docker compose up --build
docker compose exec api alembic upgrade head
docker compose exec api python -m app.ingestion.run_ingestion
docker compose exec api python -m app.graph.run_graph_load
docker compose exec api python -m app.graph.run_commit_graph_load
docker compose exec api python -m app.embeddings.run_embedding
docker compose exec api python -m app.investigate.check_investigate
docker compose exec api pytest tests/ -v
```