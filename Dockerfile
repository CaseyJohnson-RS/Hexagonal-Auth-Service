FROM astral/uv:python3.10-alpine

WORKDIR /auth-service

COPY uv.lock pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

COPY . .

EXPOSE 8000

ENTRYPOINT ["uv", "run"]