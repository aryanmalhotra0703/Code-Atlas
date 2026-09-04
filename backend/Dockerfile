FROM python:3.11-slim

WORKDIR /app

# Copy requirements first (not the whole app) so Docker can cache this layer.
# As long as requirements.txt doesn't change, `docker compose build` skips
# reinstalling packages even if you edit app code — much faster rebuilds.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence-transformers model at build time and bake it
# into the image. Without this, Render's free tier re-downloads ~90MB from
# Hugging Face on every cold start. With Render's bandwidth throttling that
# download takes 2-3 minutes, which exceeds Render's HTTP request timeout
# and kills the first /api/investigate call with a 502/504 before it can
# respond. Baking the model into the image means it's always available
# instantly — the only cost is a slightly larger image and a longer first
# build, both of which are fine for a deployed service.
#
# HF_HOME controls where Hugging Face caches models. Setting it here (and
# in the CMD environment via ENV) ensures pipeline.py's SentenceTransformer
# load finds the pre-downloaded weights in the same location at runtime.
ENV HF_HOME=/app/.hf_cache
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY app ./app
COPY alembic.ini .
COPY alembic ./alembic
COPY tests ./tests

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
