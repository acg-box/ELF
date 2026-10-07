FROM python:3.13-slim-trixie

COPY config/benchmark/locks/openviking.txt /opt/benchmark/locks/openviking.txt
RUN pip install --no-cache-dir --only-binary=:all: \
  --require-hashes --requirement /opt/benchmark/locks/openviking.txt

COPY scripts/benchmark-unit.py /opt/benchmark/benchmark-unit.py
COPY scripts/benchmark_targets /opt/benchmark/benchmark_targets
ENV PYTHONUNBUFFERED=1
CMD ["python3", "/opt/benchmark/benchmark-unit.py", "--target", "openviking"]
