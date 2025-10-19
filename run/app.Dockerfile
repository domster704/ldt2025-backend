FROM python:3.12-slim AS base

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Moscow

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists \
    rm -f /var/lib/apt/lists/lock /var/cache/apt/archives/lock /var/lib/dpkg/lock-frontend && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      ca-certificates libpq5 libstdc++6 curl && \
    rm -rf /var/lib/apt/lists/*

FROM base AS builder

ARG POETRY_VERSION=2.1.4

ENV VENV_PATH=/opt/venv \
    POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false
ENV PATH="${VENV_PATH}/bin:${POETRY_HOME}/bin:${PATH}" \
    VIRTUAL_ENV="${VENV_PATH}"

RUN curl -sSLf https://install.python-poetry.org | python - --version "${POETRY_VERSION}" && \
    ln -sf "${POETRY_HOME}/bin/poetry" /usr/local/bin/poetry

RUN python -m venv "${VENV_PATH}"

WORKDIR /build

RUN --mount=type=cache,target=/root/.cache/pypoetry \
    --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=poetry.lock,target=poetry.lock \
    --mount=type=bind,source=README.md,target=README.md \
    poetry install --only main --no-root --no-ansi --no-interaction

COPY src/app /build/src/app

RUN --mount=type=cache,target=/root/.cache/pypoetry \
    --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=poetry.lock,target=poetry.lock \
    --mount=type=bind,source=README.md,target=README.md \
    bash -lc 'poetry build -f wheel && pip install --no-deps --no-cache-dir dist/*.whl' && \
    python -m compileall -q .

FROM base AS runtime

ARG VCS_REF=""
LABEL org.opencontainers.image.title="lc2025-server" \
      org.opencontainers.image.description="REST API server for project" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.revision=$VCS_REF \
      org.opencontainers.image.source="https://github.com/domster704/lct2025" \
      org.opencontainers.image.licenses="MIT"

RUN useradd -u 10001 -m appuser


COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/src/app /home/app
ENV PATH="/opt/venv/bin:${PATH}" \
    VIRTUAL_ENV="/opt/venv" \
    PYTHONPATH="/home/app:${PYTHONPATH}"

WORKDIR /home

COPY ./app/static ./static
COPY ./app.db .

EXPOSE 8000

ENTRYPOINT ["python", "/home/app/main.py"]
