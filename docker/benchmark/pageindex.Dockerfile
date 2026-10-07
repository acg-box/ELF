FROM python:3.11-bookworm

COPY config/benchmark/locks/pageindex.txt /opt/benchmark/locks/pageindex.txt
RUN pip install --no-cache-dir --only-binary=:all: \
  --require-hashes --requirement /opt/benchmark/locks/pageindex.txt

COPY scripts/benchmark-unit.py /opt/benchmark/benchmark-unit.py
COPY scripts/benchmark_targets /opt/benchmark/benchmark_targets
ENV PYTHONUNBUFFERED=1
ENV OPENAI_AGENTS_DISABLE_TRACING=1
CMD ["python3", "/opt/benchmark/benchmark-unit.py", "--target", "pageindex"]
