FROM python:3.15-slim@sha256:94d3426f1def7db4a106a232ac121bfd975393e5dfd40a619b955fae45fe7913

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