FROM python:3.11-bookworm

COPY config/benchmark/locks/mem0.txt /opt/benchmark/locks/mem0.txt
RUN pip install --no-cache-dir --only-binary=:all: \
  --require-hashes --requirement /opt/benchmark/locks/mem0.txt

COPY scripts/benchmark-unit.py /opt/benchmark/benchmark-unit.py
COPY scripts/benchmark_targets /opt/benchmark/benchmark_targets
ENV MEM0_TELEMETRY=false
ENV PYTHONUNBUFFERED=1
CMD ["python3", "/opt/benchmark/benchmark-unit.py", "--target", "mem0"]
