FROM python:3.10-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

COPY pyproject.toml README.md /build/
COPY src /build/src

RUN python -m pip install --upgrade pip && \
    python -m pip wheel --wheel-dir /dist .


FROM python:3.10-slim AS runtime

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --create-home --home-dir /home/alfred --shell /usr/sbin/nologin alfred

COPY --from=builder /dist /tmp/dist

RUN python -m pip install /tmp/dist/*.whl && \
    rm -rf /tmp/dist

USER alfred

EXPOSE 8000

CMD ["alfred", "serve", "--host", "0.0.0.0", "--port", "8000"]
