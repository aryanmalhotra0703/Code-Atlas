FROM python:3.11-slim

WORKDIR /app

# Copy requirements first (not the whole app) so Docker can cache this layer.
# As long as requirements.txt doesn't change, `docker compose build` skips
# reinstalling packages even if you edit app code — much faster rebuilds.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic.ini .
COPY alembic ./alembic
COPY tests ./tests

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
