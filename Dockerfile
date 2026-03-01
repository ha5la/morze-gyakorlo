FROM python:3.12-alpine@sha256:70a8c8126819e6b13173dce46a79d15114624b1daf0609d008abddfd7124aa77 AS base
FROM base AS builder

RUN apk add --no-cache gcc g++ musl-dev

COPY --from=ghcr.io/astral-sh/uv:0.9.28@sha256:3afd9017d8cfe0f9749afdedeb6c39a3896388fdfb1bd43434d9d5e83f7a20b7 /uv /usr/local/bin/uv

WORKDIR /app
COPY .python-version pyproject.toml uv.lock /app/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

FROM base AS runtime

RUN apk add --no-cache ffmpeg

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY *.py /app/
COPY corpus /app/corpus

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["python", "main.py"]
CMD ["35", "10"]
