FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY prompts /app/prompts
COPY scripts /app/scripts

RUN python -m pip install --upgrade pip \
    && python -m pip install -e .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "mordecai.main:app", "--host", "0.0.0.0", "--port", "8000"]