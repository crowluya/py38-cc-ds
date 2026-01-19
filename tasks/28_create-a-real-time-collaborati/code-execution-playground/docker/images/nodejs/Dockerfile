FROM node:20-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Add non-root user
RUN useradd -m -u 1000 coder && \
    chown -R coder:coder /workspace

USER coder

ENV NODE_ENV=production

CMD ["node"]
