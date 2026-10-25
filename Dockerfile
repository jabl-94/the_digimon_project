FROM python:3.11-slim@sha256:b7a9e5f6a93d6d4a31f129bbd4bdee69efccb6ded0fb230d78aafaf37af98377

WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN groupadd --system digifarm \
    && useradd --system --gid digifarm --create-home digifarm \
    && mkdir -p /workspace/data \
    && chown digifarm:digifarm /workspace/data

COPY --chown=digifarm:digifarm src ./src

USER digifarm

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]