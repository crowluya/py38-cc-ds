# Real-Time Collaborative Code Execution Playground

A full-stack real-time code execution platform with Rust WebSocket backend, Docker containerization, and React frontend.

## Architecture

- **Backend**: Rust with tokio-tungstenite for WebSocket handling
- **Execution**: Docker containers for isolated code execution
- **Frontend**: React with Vite, Monaco Editor, and WebSocket client
- **Storage**: SQLite for session history

## Supported Languages

- Python 3.x
- JavaScript/Node.js
- Rust
- Go
- More coming soon...

## Features

- Real-time code execution with output streaming
- Multi-user collaboration on sessions
- Session history and persistence
- Syntax highlighting with Monaco Editor
- Safe execution in Docker containers
- Multiple programming language support

## Prerequisites

- Docker and Docker Compose
- Rust 1.70+ (with cargo)
- Node.js 18+ (with npm/yarn)
- SQLite 3

## Getting Started

### Backend Setup

```bash
cd backend
cargo build
cargo run
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Docker Setup

```bash
# Build language images
docker build -t code-exec-python ./docker/images/python
docker build -t code-exec-node ./docker/images/nodejs
docker build -t code-exec-rust ./docker/images/rust
docker build -t code-exec-go ./docker/images/go
```

## API Documentation

See [API.md](./backend/API.md) for detailed API documentation.

## License

MIT
