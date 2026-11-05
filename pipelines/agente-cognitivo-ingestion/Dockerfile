FROM python:3.12-slim-bookworm
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps .
CMD ["agente-cognitivo-ingestion"]
