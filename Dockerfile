FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd --system --gid 10001 brain && useradd --system --uid 10001 --gid brain brain

COPY mcp/requirements.txt /app/mcp/requirements.txt
RUN python -m pip install --upgrade pip && python -m pip install -r /app/mcp/requirements.txt

COPY --chown=brain:brain . /app
USER brain

EXPOSE 8085
CMD ["python", "/app/mcp/server.py"]
