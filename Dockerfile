
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Runtime library required by numerical/ML dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies

# Install Python dependencies
COPY requirements.txt .

RUN python -m pip install --upgrade pip

# Install CPU-only PyTorch for Linux ARM64 / Apple Silicon Docker
RUN python -m pip install \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple \
    "torch==2.15.0+cpu"

# Install remaining application dependencies
RUN python -m pip install -r requirements.txt


# Copy application source
COPY config/ ./config/
COPY api/ ./api/
COPY validation/ ./validation/
COPY database/ ./database/
COPY retrieval/ ./retrieval/
COPY ingestion/ ./ingestion/
COPY services/ ./services/
COPY agents/ ./agents/
COPY worker/ ./worker/
COPY observability/ ./observability/
COPY evaluation/ ./evaluation/
COPY load_testing/ ./load_testing/

# Copy monitoring configuration and create persistent storage directory
COPY monitoring/ ./monitoring/

RUN mkdir -p /app/storage/chroma \
    /app/storage/prometheus \
    /app/storage/quarantine \
    && useradd --create-home appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
