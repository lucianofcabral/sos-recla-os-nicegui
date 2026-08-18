# syntax=docker/dockerfile:1

FROM python:3.13-slim AS builder

# Install uv (latest release) into /usr/local/bin.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Use the system Python across both stages.
ENV UV_PYTHON_DOWNLOADS=0 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first (layer-cached); skip the project itself.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project --no-editable

# Copy the project and install it (non-editable) into the venv.
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    UI_HOST="0.0.0.0" \
    UI_PORT="8081"

WORKDIR /app

# Copy the environment, but not the source code.
COPY --from=builder /app/.venv /app/.venv
# Keep helper scripts (bootstrap, import) available inside the container.
COPY --from=builder /app/scripts /app/scripts

EXPOSE 8081

# NiceGUI needs a writable storage dir; the app creates the DB schema on boot.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8081/', timeout=5)"

CMD ["python", "-m", "src.ui.main"]