FROM rust:1-bookworm AS elf-builder

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    clang \
    cmake \
    libssl-dev \
    pkg-config \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY Cargo.toml Cargo.lock build.rs rust-toolchain.toml ./
COPY apps ./apps
COPY packages ./packages
COPY config ./config
COPY sql ./sql

RUN --mount=type=cache,id=elf-benchmark-cargo-registry,target=/usr/local/cargo/registry \
  --mount=type=cache,id=elf-benchmark-cargo-git,target=/usr/local/cargo/git \
  --mount=type=cache,id=elf-benchmark-cargo-target,target=/src/target \
  cargo build --locked --release -p elf-eval --bin real_world_live_adapter \
  && install -D /src/target/release/real_world_live_adapter \
    /out/real_world_live_adapter

FROM node:22-bookworm AS qmd-builder

ARG QMD_REVISION=facd35e01359e59d938bc9418e93fb9318addee3

RUN apt-get update \
  && apt-get install -y --no-install-recommends git \
  && rm -rf /var/lib/apt/lists/*

RUN git init /opt/qmd \
  && git -C /opt/qmd remote add origin https://github.com/tobi/qmd.git \
  && git -C /opt/qmd fetch --depth=1 origin "${QMD_REVISION}" \
  && git -C /opt/qmd checkout --detach FETCH_HEAD

WORKDIR /opt/qmd
COPY config/benchmark/locks/qmd-overrides.json /opt/qmd-overrides.json
COPY config/benchmark/locks/qmd-package-lock.json /opt/qmd/package-lock.json
RUN node --input-type=module -e 'import fs from "node:fs"; const p=JSON.parse(fs.readFileSync("package.json")); p.overrides={...p.overrides,...JSON.parse(fs.readFileSync("/opt/qmd-overrides.json"))}; fs.writeFileSync("package.json",JSON.stringify(p,null,2)+"\n");' \
  && npm ci --ignore-scripts \
  && npm rebuild better-sqlite3 node-llama-cpp --foreground-scripts \
  && npm run build

FROM python:3.11-bookworm AS elf-runtime

ARG ELF_SOURCE_COMMIT=unknown
COPY --from=elf-builder /out/real_world_live_adapter /usr/local/bin/real_world_live_adapter
COPY config/local/elf.docker.toml /opt/elf/
COPY config/local/tokenizer.wordlevel.json /config/local/tokenizer.wordlevel.json
COPY scripts/benchmark-unit.py /opt/benchmark/benchmark-unit.py
COPY scripts/benchmark_targets /opt/benchmark/benchmark_targets
LABEL org.opencontainers.image.revision="${ELF_SOURCE_COMMIT}"
ENV PYTHONUNBUFFERED=1
WORKDIR /
CMD ["python3", "/opt/benchmark/benchmark-unit.py", "--target", "elf"]

FROM elf-builder AS elf-service-builder
RUN --mount=type=cache,id=elf-benchmark-cargo-registry,target=/usr/local/cargo/registry \
  --mount=type=cache,id=elf-benchmark-cargo-git,target=/usr/local/cargo/git \
  --mount=type=cache,id=elf-benchmark-cargo-target,target=/src/target \
  cargo build --locked --release -p elf-api -p elf-worker \
  && install -D /src/target/release/elf-api /out/elf-api \
  && install -D /src/target/release/elf-worker /out/elf-worker

FROM elf-runtime AS elf-service-runtime
COPY --from=elf-service-builder /out/elf-api /usr/local/bin/elf-api
COPY --from=elf-service-builder /out/elf-worker /usr/local/bin/elf-worker

FROM qmd-builder AS qmd-runtime

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 \
  && rm -rf /var/lib/apt/lists/*
COPY --from=elf-builder /out/real_world_live_adapter /usr/local/bin/real_world_live_adapter
COPY scripts/benchmark-unit.py /opt/benchmark/benchmark-unit.py
COPY scripts/benchmark_targets /opt/benchmark/benchmark_targets
ENV XDG_CACHE_HOME=/opt/qmd-cache
ENV QMD_FORCE_CPU=1
ENV PYTHONUNBUFFERED=1
RUN npx tsx /opt/benchmark/benchmark_targets/qmd_models.mts
RUN npm prune --omit=dev --ignore-scripts
CMD ["python3", "/opt/benchmark/benchmark-unit.py", "--target", "qmd"]

FROM node:22-bookworm

ARG ELF_SOURCE_COMMIT=unknown

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    python3 \
    python3-pip \
  && rm -rf /var/lib/apt/lists/*

COPY config/benchmark/locks/mem0.txt /opt/benchmark/locks/mem0.txt
RUN python3 -m pip install --break-system-packages --no-cache-dir \
  --require-hashes --requirement /opt/benchmark/locks/mem0.txt

COPY --from=elf-builder /out/real_world_live_adapter \
  /usr/local/bin/real_world_live_adapter
COPY --from=qmd-builder /opt/qmd /opt/qmd
COPY config/local/elf.docker.toml /opt/elf/
COPY config/local/tokenizer.wordlevel.json /config/local/tokenizer.wordlevel.json
COPY scripts/benchmark-unit.py /opt/benchmark/benchmark-unit.py
COPY scripts/benchmark-provider-preflight.py /opt/benchmark/benchmark-provider-preflight.py
COPY scripts/benchmark_targets /opt/benchmark/benchmark_targets

LABEL org.opencontainers.image.revision="${ELF_SOURCE_COMMIT}"

ENV MEM0_TELEMETRY=false
ENV PYTHONUNBUFFERED=1

WORKDIR /

CMD ["python3", "/opt/benchmark/benchmark-unit.py", "--help"]
