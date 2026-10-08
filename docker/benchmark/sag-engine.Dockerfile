FROM python:3.11-bookworm

COPY config/benchmark/locks/sag-engine.txt /opt/benchmark/locks/sag-engine.txt
RUN pip install --no-cache-dir --only-binary=:all: \
  --require-hashes --requirement /opt/benchmark/locks/sag-engine.txt

COPY scripts/benchmark-unit.py /opt/benchmark/benchmark-unit.py
COPY scripts/benchmark_targets /opt/benchmark/benchmark_targets
ENV PYTHONUNBUFFERED=1
CMD ["python3", "/opt/benchmark/benchmark-unit.py", "--target", "sag-engine"]
