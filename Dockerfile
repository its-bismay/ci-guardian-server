FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

ENV PYTHONPATH=/app

EXPOSE 10000

CMD uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 10000
