FROM python:3.11-bookworm
COPY scripts/benchmark-unit.py /opt/benchmark/benchmark-unit.py
COPY scripts/benchmark_targets /opt/benchmark/benchmark_targets
ENV PYTHONUNBUFFERED=1
CMD ["python3", "/opt/benchmark/benchmark-unit.py", "--help"]
