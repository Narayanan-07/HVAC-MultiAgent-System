# ── HVAC Multi-Agent System · Backend image ──────────────────────────────
# FastAPI + CrewAI pipeline. The large data/ directory is NOT baked into the
# image — mount it as a volume (see docker-compose.yml).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# System dependencies:
#   chromium             -> Plotly static image export (kaleido)
#   libpango/cairo/gdk   -> WeasyPrint runtime libs (PDF rendering on Linux)
#   fonts-dejavu         -> fallback fonts for the report (Aptos is Windows-only)
#   build tools          -> compiling prophet / xgboost wheels if needed
# NOTE: wkhtmltopdf was removed from Debian 13 (trixie); the backend renders
# PDFs with WeasyPrint on Linux and only uses wkhtmltopdf on a Windows dev box.
RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium \
        build-essential \
        libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
        libffi-dev libcairo2 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium \
    BROWSER_PATH=/usr/bin/chromium

WORKDIR /app

# Install Python deps first for better layer caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Application code (data/ and reports/ come in as mounted volumes)
COPY backend/ ./backend/
COPY scripts/ ./scripts/

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
