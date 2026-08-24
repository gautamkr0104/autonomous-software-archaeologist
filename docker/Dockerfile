FROM python:3.11-slim AS backend

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir ".[dev]"

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "asa.api.app:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
