FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Add non-root user
RUN useradd -m -u 1000 coder && \
    chown -R coder:coder /workspace

USER coder

# Set resource limits
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["python3"]
