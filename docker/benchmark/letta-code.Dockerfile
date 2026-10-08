FROM node:22-bookworm

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 git \
  && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/letta
COPY config/benchmark/locks/letta-code-package.json ./package.json
COPY config/benchmark/locks/letta-code-package-lock.json ./package-lock.json
ENV SCARF_ANALYTICS=false
RUN npm ci --ignore-scripts \
  && node node_modules/@letta-ai/letta-code/scripts/postinstall-patches.js
ENV PATH="/opt/letta/node_modules/.bin:${PATH}"
ENV LETTA_LOCAL_BACKEND_EXPERIMENTAL=1
CMD ["letta", "--help"]
