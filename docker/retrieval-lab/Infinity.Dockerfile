# Official v0.7.4 ARM64 binary requires glibc >= 2.38; its Ubuntu 22.04 image has 2.35.
FROM infiniflow/infinity:v0.7.4-arm64 AS upstream
FROM debian:trixie-slim
RUN apt-get update && apt-get install -y --no-install-recommends libatomic1 && rm -rf /var/lib/apt/lists/*
COPY --from=upstream /usr/bin/infinity /usr/bin/infinity
COPY --from=upstream /usr/share/infinity /usr/share/infinity
ENTRYPOINT ["/usr/bin/infinity"]
