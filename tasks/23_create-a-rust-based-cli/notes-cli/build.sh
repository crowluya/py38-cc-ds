#!/bin/bash

# Build script for Notes CLI

set -e

echo "🔨 Building Notes CLI..."

# Check if Rust is installed
if ! command -v cargo &> /dev/null; then
    echo "❌ Error: Rust/Cargo not found. Please install Rust first."
    echo "Visit: https://rustup.rs/"
    exit 1
fi

echo "📦 Running tests..."
cargo test

echo "🏗️  Building release binary..."
cargo build --release

echo "✅ Build complete!"
echo ""
echo "Binary location: target/release/notes"
echo ""
echo "To install system-wide, run:"
echo "  cargo install --path ."
echo ""
echo "Or copy the binary manually:"
echo "  sudo cp target/release/notes /usr/local/bin/"
