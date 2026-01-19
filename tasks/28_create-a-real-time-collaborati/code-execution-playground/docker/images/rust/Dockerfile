FROM rust:1.75-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Add non-root user
RUN useradd -m -u 1000 coder && \
    chown -R coder:coder /workspace

USER coder

ENV CARGO_TERM_COLOR=always

CMD ["sh"]
