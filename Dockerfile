FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir ".[dev]" && pip install --no-cache-dir cryptography

RUN mkdir -p .harness/memory

EXPOSE 8080

CMD ["python", "-m", "pyharness.main"]