FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

# Install astral UV runtime
COPY --from=ghcr.io/astral-sh/uv:0.6.13 /uv /uvx /bin/
ENV PATH="/app/.venv/bin:$PATH"
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update \
 && apt-get install --no-install-recommends -y git openssh-client \
 && rm -rf /var/lib/apt/lists/*


COPY ./pyproject.toml ./uv.lock /app/


RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

ENV PYTHONPATH=/app

# Copy project files
COPY ./main.py /app/main.py
COPY ./src /app/src

# Final sync (optional, but safe)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

# Launch FastAPI with uvicorn with reload for development
CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "7000"]