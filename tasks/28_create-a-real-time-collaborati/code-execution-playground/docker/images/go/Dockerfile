FROM golang:1.21-alpine

RUN apk add --no-cache procps

WORKDIR /workspace

# Add non-root user
RUN adduser -D -u 1000 coder && \
    chown -R coder:coder /workspace

USER coder

ENV GO111MODULE=on

CMD ["go"]
