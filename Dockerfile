FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY README.md ./
COPY src ./src
COPY app ./app
COPY static ./static
COPY data ./data
COPY alembic.ini ./
COPY alembic ./alembic

RUN pip install --no-cache-dir uv \
    && uv pip install --system -e .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]