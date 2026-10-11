FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && rm -rf /var/lib/apt/lists/*
COPY docker/retrieval-lab/requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
RUN pip install --no-cache-dir pgvector==0.4.2
ENV PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4
WORKDIR /repo
ENTRYPOINT ["python", "scripts/benchmark-retrieval-lab.py"]
