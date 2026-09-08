# Code Atlas — Project Notes

Reference notes covering everything built and explained through the
Neo4j incremental sync fix.
Demo repo: `httpie/cli`

---

## 1. Core Concepts (the "why" behind the tools)

### Containers
A container is a sealed, portable box holding a program plus everything it
needs to run (exact language version, libraries, config) — separate from
whatever is installed on the host machine. This is what makes "it works on
my machine" problems mostly disappear: the container brings its own
environment with it, so it behaves identically everywhere.

Different from a full virtual machine: a VM emulates an entire computer
(its own OS kernel, slow to boot, heavy). A container shares the host
machine's kernel and only isolates the application layer — much lighter,
starts in seconds.

### Docker / Docker Desktop
- **Docker** — the tool that builds and runs containers.
- **Docker Desktop** — the actual application you open to use Docker, with
  a visual interface (container list, logs, exec shell, etc.).

### WSL2 (Windows Subsystem for Linux)
Docker containers are built expecting a Linux kernel underneath them.
Windows' own kernel isn't Linux, so Docker Desktop on Windows needs WSL2 —
a real, lightweight Linux environment running inside Windows — to actually
place containers onto. Without WSL2 installed, Docker Desktop has nowhere
valid to run anything.

### Docker Compose (`docker-compose.yml`)
Docker itself runs one container at a time. Compose is the layer above
that: it starts multiple containers together, puts them on a shared
private network so they can reach each other **by service name** instead
of `localhost` (e.g. `postgres`, `neo4j`), and controls startup order via
healthchecks.

### Healthchecks & `depends_on: condition: service_healthy`
Plain `depends_on` only waits for a container to *start*, not to be
*ready*. A healthcheck actually tests readiness (e.g. "can Postgres accept
a real connection?"). `condition: service_healthy` makes one service wait
for another's healthcheck to pass before starting.

`start_period` gives a service a grace window where failed checks don't
count against its retry budget — added after Neo4j occasionally needed
longer than 25s to boot.

### Named volumes vs. bind mounts
- **Named volume** (`postgres_data`, `neo4j_data`, `model_cache`) —
  Docker-managed storage that persists data across restarts.
- **Bind mount** (`./backend/app:/app/app`) — syncs a local folder into
  the running container live, which is what makes `--reload` pick up
  code edits without rebuilding. Note: only `app/` is bind-mounted —
  `alembic/` and `tests/` are not, so new files under either need a
  rebuild (`--build`) to actually appear inside the container.

### API & Endpoints
An API is a defined way for one program to ask another for something.
An **endpoint** is one specific thing the API knows how to do, tied to a
URL (e.g. `/health`).

### Why `/health` actually queries the databases
A health check that only returns `{"ok": true}` without touching its
dependencies can report "healthy" while a database is actually
unreachable. Ours runs a real query against Postgres and a real
connectivity check against Neo4j.

### Environment variables & `.env`
- `.env` — real, private values (like API tokens). Never committed.
- `.env.example` — a safe template with placeholder values.
- In Docker, `.env` is not read directly — `docker-compose.yml` must
  explicitly forward each variable via `${VAR_NAME}`.

### Pydantic Settings (`config.py`)
One typed class instead of `os.environ.get()` scattered everywhere.
Missing/malformed values fail loudly at startup instead of causing a
confusing error deep in unrelated code later.

### SQLAlchemy (ORM)
Lets you define database tables as Python classes instead of writing raw
SQL by hand. `create_engine()` is lazy — it doesn't connect until the
first real query runs.

### Alembic (migrations)
Turns changes to your SQLAlchemy models into tracked, repeatable database
schema changes. `alembic upgrade head` applies pending migrations.

### GitHub REST API basics
- **Auth** — a personal access token, sent as a Bearer header (5,000
  requests/hour vs. 60 unauthenticated).
- **Pagination** — signaled via the response's `Link` HTTP header, not
  the JSON body.
- **`raise_for_status()`** — turns a failed request into an immediate
  exception instead of silently returning an error message as if it
  were real data.
- **Always set a `timeout`** — without one, a stalled connection can
  hang indefinitely.

### Idempotency
An operation is idempotent if running it once and running it many times
leaves the same end state. Used throughout: `ON CONFLICT DO NOTHING`
(Postgres) and `MERGE` (Neo4j Cypher) are the same underlying idea,
expressed in each database's own vocabulary.

### Incremental sync via watermarks
Tracking a "last synced at" timestamp per repo, then only fetching
records newer than that timestamp on subsequent runs. Used for Postgres
ingestion (`last_synced_at` + GitHub's `since` filter) and, later, for
Neo4j graph loading (`last_commit_graph_sync_at`,
`last_pr_graph_sync_at`) — same pattern, applied a second time to a
different layer of the pipeline.

---

## 2. Milestone 0 — Scaffold

**Goal:** three services (API, Postgres, Neo4j) running together in
Docker, verified healthy.

| File | Purpose |
|---|---|
| `docker-compose.yml` | Defines and networks the three services; healthchecks control startup order |
| `backend/Dockerfile` | Builds the API's container image; installs dependencies before copying app code |
| `backend/requirements.txt` | Python dependencies |
| `backend/app/main.py` | FastAPI app; `/health` endpoint verifying real DB connectivity |
| `backend/app/core/config.py` | Typed settings loaded from environment variables |
| `.env` / `.env.example` | Real secrets (gitignored) / safe template |
| `.gitignore` | Excludes `.venv`, `.env`, cache files from git |
| `.github/workflows/ci.yml` | Builds the stack on every push, runs the test suite, polls `/health` |

**Key commands:**
```bash
docker compose up --build       # build + start all services
docker compose up               # start without rebuilding
docker compose exec api <cmd>   # run a command inside the running api container
```

---

## 3. Milestone 1 — GitHub Ingestion

**Goal:** pull real data (repo metadata, commits, PRs) from `httpie/cli`
into Postgres, incrementally.

| File | Purpose |
|---|---|
| `backend/app/ingestion/github_client.py` | GitHub API calls: auth, pagination, timeouts, per-commit/per-PR detail fetches, `RepoNotFoundError` for missing/inaccessible repos |
| `backend/app/models/raw.py` | SQLAlchemy models: `RawRepository`, `RawCommit`, `RawPullRequest` |
| `backend/app/db/session.py` | DB engine (with `pool_pre_ping`/`pool_recycle` for cloud Postgres), session factory, `Base` |
| `backend/alembic.ini`, `alembic/env.py`, `alembic/script.py.mako` | Alembic configuration |
| `backend/alembic/versions/0001_create_raw_tables.py` | First migration |
| `backend/alembic/versions/0002_add_last_synced_at.py` | Adds incremental-sync tracking column |
| `backend/app/ingestion/pipeline.py` | Fetches + stores idempotently; incremental via GitHub's `since` filter |
| `backend/app/ingestion/run_ingestion.py` | Runs the full pipeline |

**Key commands:**
```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m app.ingestion.run_ingestion
docker compose exec postgres psql -U atlas -d atlas -c "<SQL>"
```

**Verified result:** real repo metadata, 200 commits, 225 PRs stored
(count grows over time — httpie is a live, actively developed repo);
re-running ingestion correctly fetches only what's new since last sync.

---

## 4. Milestone 2 — Import Graph, Ownership, Traversal

**Goal:** turn raw ingested data into an actual connected graph in Neo4j.

| File | Purpose |
|---|---|
| `backend/app/ingestion/repo_source.py` | Downloads real repo source as a tarball, no `git` binary needed |
| `backend/app/ingestion/parser/python_imports.py` | AST-based import extraction |
| `backend/app/ingestion/parser/import_resolver.py` | Resolves raw import names to real file paths (heuristic) |
| `backend/app/graph/neo4j_client.py` | Shared Neo4j driver instance |
| `backend/app/graph/loader.py` | Writes nodes/edges via `MERGE` (idempotent), batched with `UNWIND`: File, Commit, Person, IMPORTS, AUTHORED, MODIFIES, OWNED_BY, CONTAINS |
| `backend/app/graph/queries.py` | Traversal: blast radius, recent nearby changes, ownership, files-for-commit, commits-for-PR, module graph, file count |
| `backend/app/graph/run_graph_load.py` | Loads the import graph; repo label derived from the same owner/repo used to download, never a separate constant |
| `backend/app/graph/run_commit_graph_load.py` | Loads commit/author graph, incrementally (see Milestone 8) |
| `backend/app/graph/run_pr_links_load.py` | Bulk PR→commit linking, incrementally (see Milestone 8) |
| `backend/app/graph/sync_state.py` | Tracks graph-level sync watermarks per repo |

**Verified result:** 381 real import edges resolved, 122+ File nodes
(grows as the live repo changes), a genuine import cycle surfaced
automatically, derived ownership from edit frequency.

**Real bug caught and fixed:** a different GitHub repo (a student's
class-assignment fork of httpie) was accidentally downloaded and loaded
into the graph, but mislabeled as `httpie/cli` because the label was a
separate hardcoded constant instead of being derived from the actual
owner/repo used to download. Fixed by deriving the label directly from
those same values, making the mismatch structurally impossible going
forward.

---

## 5. Milestone 3 — Embeddings & Retrieval

**Goal:** search by meaning, not exact wording.

| File | Purpose |
|---|---|
| `backend/app/models/embedding.py` | `Embedding` model, links to source via `(repo_id, source_type, source_id)` |
| `backend/alembic/versions/0003_add_embeddings_table.py` | Enables `pgvector`, creates the `embeddings` table |
| `backend/app/embeddings/pipeline.py` | Local model (`all-MiniLM-L6-v2`), lazy-loaded on first use (not at import time — avoids OOM on constrained hosts), embeds commit/PR text, stores idempotently |
| `backend/app/retrieval/search.py` | Embeds a query, finds closest vectors via cosine distance |

**Verified result:** query *"SSL certificate verification is failing"*
correctly surfaced real, relevant results despite sharing almost no
exact wording.

---

## 6. Milestone 4 — Connecting Retrieval to the Graph (core deliverable)

**Goal:** query in, ranked and explained answer out — real files,
owners, blast radius, ranked by a custom composite score.

| File | Purpose |
|---|---|
| `backend/app/investigate/engine.py` | `investigate()` — retrieves candidates, walks the graph to real files, attaches owner + blast radius, lazy-loads missing graph detail on demand, re-ranks by composite score |
| `backend/app/investigate/ranking.py` | Composite scoring: 50% similarity + 30% recency (exponential decay) + 20% blast radius (log-scaled), returns full breakdown not just the total |
| `backend/app/investigate/check_investigate.py` | End-to-end proof script |

**Key design choice:** lazy loading over bulk pre-loading — `investigate()`
checks the graph first and fetches+loads on demand if a needed link is
missing, guaranteeing any retrieved result gets full traversal rather
than only ones a fixed batch limit happened to cover.

**Verified result:** query *"SSL certificate verification is failing"*
returned 5 results, all fully traced, correctly surfacing that
`httpie/compat.py` (blast radius: 54 files) is the common thread across
most SSL-related fixes — found automatically, not searched for directly.
The composite ranking changed real outcomes: a result with lower raw
similarity but higher recency/blast-radius outranked one with higher
raw similarity.

---

## 7. Milestone 5 — API & Frontend

**Goal:** make the engine reachable by anyone, not just via terminal scripts.

| File | Purpose |
|---|---|
| `backend/app/api/routes.py` | `/api/investigate`, `/api/architecture`, `/api/stats` — real HTTP endpoints with proper error handling (empty query rejection, repo-not-found, generic 500 fallback, low-confidence result warnings) |
| `backend/app/main.py` | CORS setup, route registration |
| `frontend/src/App.tsx` | Sidebar shell, wired to real repo stats |
| `frontend/src/InvestigateView.tsx` | Hero header, search, example query chips, query history, result list, score breakdown bars, file cards (HOT badge, owner avatars, blast radius bars), loading skeleton |
| `frontend/src/ArchitectureView.tsx` | Module-level view with a 2D force-directed graph (`react-force-graph-2d`) |
| `frontend/src/TraceGraph3D.tsx` | 3D blast-radius graph per result (`3d-force-graph`), expandable |

---

## 8. Milestone 6/7 — Tests, Performance, Deployment, Incremental Sync

**Tests:** 14 tests across `test_import_resolver.py`, `test_ranking.py`,
`test_github_client.py` — locking in real, previously hand-verified
behaviors, run automatically in CI on every push.

**Performance:** stress-tested against `django/django` (2,930 files,
~9,000 edges) instead of only the small httpie demo. Found the Neo4j
graph-load step taking 83.5s (89% of total time) due to one network
round-trip per edge; fixed with `UNWIND` batching, cutting it to 26.7s
(3.1x). Separately found PyTorch's default install pulling in ~2GB of
unused NVIDIA GPU tooling; switched to the CPU-only build, cutting
Docker build time from ~18 minutes to ~3.

**Deployment:** moved from one local Docker Compose file to four
separate cloud services — Neo4j Aura (graph), Neon (Postgres +
pgvector), Render (API), frontend still local. Real issues hit and
fixed along the way: an env var name mismatch (`NEO4J_USERNAME` vs
`NEO4J_USER`), `--reload` crashing the container on Render's free tier
(dev-only feature, removed for production), Neon closing idle
connections (fixed with `pool_pre_ping`/`pool_recycle`), an eager model
load causing an out-of-memory crash on Render's 512MB free tier (fixed
with lazy loading), and a genuine `UnboundLocalError` in `routes.py`
(a `message = None` line sat unreachably inside an `except` block after
a `raise`, crashing any query that returned a genuinely good,
high-confidence result). Deployment status: Neo4j Aura and Neon fully
verified with real data; Render backend deploys and stays live, but
`/api/investigate` still returns an error under active investigation
(handed off with full context to a second debugging session).

**Neo4j incremental sync:** `run_commit_graph_load.py` and
`run_pr_links_load.py` now track `last_commit_graph_sync_at` and
`last_pr_graph_sync_at` on the repo row, only processing commits/PRs
newer than the last graph sync — same watermark pattern already used
for Postgres ingestion, applied to the graph layer. Verified: a second
consecutive run of `run_pr_links_load` processed 0 PRs after the first
run processed 50.

---

## 9. Environment / Tooling Notes

- **Python 3.12** over 3.14 for the venv — newer versions sometimes
  lack prebuilt wheels for packages like `psycopg2-binary`.
- **VS Code interpreter selection** matters for import resolution.
- **New terminal (or VS Code restart) after installing new software** —
  PATH changes aren't picked up by already-open terminals.
- **New dependency → needs `--build`.**
- **New env var in `docker-compose.yml` → needs a restart.**
- **New file in `alembic/` or `tests/` → needs `--build`**, since only
  `app/` is bind-mounted live.
- **Unsaved files show an `M` badge in VS Code's tab** — several bugs
  today traced back to editing a file, believing it was saved, and it
  genuinely wasn't. Always check for the `M` before assuming a change
  took effect.
- **Cypher can't parameterize variable-length hop ranges**
  (`[:REL*1..N]`) — has to be baked into the query text directly.
- **`MERGE` needs a bound node variable**, not a property-access
  expression — extract into its own `WITH` first.
- **OneDrive-synced project folders can break Node.js dependency
  installs** — cloud-sync placeholder files can fail to download fast
  enough during bundling, causing cryptic "cloud operation was
  unsuccessful" errors. Fix: mark the folder "Always keep on this
  device" in OneDrive settings.
- **Render's free tier has no shell access** — debugging is log-only.
  Auto-deploy-on-push has been unreliable; manual "Deploy latest
  commit" is more consistent.
- **Managed cloud Postgres (Neon, etc.) closes idle connections** —
  `pool_pre_ping=True` and `pool_recycle=<seconds>` on the SQLAlchemy
  engine prevent crashes from reusing a connection the provider already
  closed.

---

## 10. Known Trade-offs & Design Decisions

- **Import resolution is a heuristic**, not a full import-system
  reimplementation.
- **Ownership (`OWNED_BY`) is derived from edit frequency**, not a fact
  GitHub provides.
- **The import graph only grows**, never reconciles deletions.
- **Bounded initial batches** mean some commits/PRs need lazy, on-demand
  loading at query time — slower on a cache-miss, correct either way.
- **Local embedding model** chosen after hitting OpenAI's payment-method
  requirement — no cost/key needed, heavier Docker build, likely
  somewhat lower quality than a larger hosted model.
- **Single-language (Python) import parsing.**
- **Incremental sync now exists for both Postgres ingestion and Neo4j
  graph loaders.** Postgres tracks `last_synced_at` and uses GitHub's
  `since` filter; Neo4j graph loaders track `last_commit_graph_sync_at`
  and `last_pr_graph_sync_at` on the repo row, only processing
  commits/PRs newer than the last graph sync. Verified: a second
  consecutive run of `run_pr_links_load` processed 0 PRs after the
  first run processed 50.
- **The import graph itself is not incrementally re-parsed** — each run
  re-downloads and re-parses the full repo. Accepted trade-off: even on
  a 2,930-file stress test (django/django), the full pipeline completes
  in under 30 seconds post-optimization, making incremental parsing not
  worth the added complexity at this scale.
- **Multi-repo support does not exist** — `REPO` is a hardcoded constant
  throughout the backend. A real re-architecture, not a small add-on.
- **Two temporary debug changes are currently live** in the deployed
  backend, added to unblock a Render debugging session: `routes.py`
  exposes raw exception messages directly in API responses instead of a
  generic message, and `main.py` prints which DB hosts it connected to
  at startup. Both should be reverted once the underlying `/api/investigate`
  deployment bug is resolved — leaking internals in a public response is
  fine for debugging, not for shipping.

---

## 11. What's Next

Open items, roughly in priority order:
- Resolve the remaining Render `/api/investigate` deployment bug
- Revert the two temporary debug changes once resolved
- Deploy the frontend (currently local-only)
- Frontend polish: architecture graph auto-fit/zoom on load without
  requiring interaction, further passes on mobile/narrow viewports
- Multi-repo support (real re-architecture, not yet started)
- A genuine "why this matched" explanation feature (deferred — needs
  its own design pass, likely template-based rather than LLM-based to
  avoid reintroducing an API cost/billing dependency)