FROM oven/bun:1.4.0

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 git ca-certificates \
  && rm -rf /var/lib/apt/lists/*

RUN git init /opt/gbrain \
  && git -C /opt/gbrain remote add origin https://github.com/garrytan/gbrain.git \
  && git -C /opt/gbrain fetch --depth=1 origin 5b5891069413b28b2fe3a50675116d67d5a1e145 \
  && git -C /opt/gbrain checkout --detach FETCH_HEAD \
  && test "$(git -C /opt/gbrain rev-parse HEAD)" = 5b5891069413b28b2fe3a50675116d67d5a1e145

WORKDIR /opt/gbrain
RUN bun install --frozen-lockfile --ignore-scripts

COPY scripts/benchmark-unit.py /opt/benchmark/benchmark-unit.py
COPY scripts/benchmark_targets /opt/benchmark/benchmark_targets
ENV PYTHONUNBUFFERED=1
CMD ["python3", "/opt/benchmark/benchmark-unit.py", "--target", "gbrain"]
