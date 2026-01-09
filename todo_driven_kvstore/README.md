# Key-Value Store

A lightweight key-value store implementation in Python.

## Overview

This project provides a simple key-value store with CLI and programmatic API access. It supports basic CRUD operations and is designed for lightweight data storage needs.

## Usage

### Installation

```bash
git clone https://github.com/username/keyvalue-store.git
cd keyvalue-store
pip install -r requirements.txt
```

### Basic Usage

```python
from kvstore import KVStore

# Initialize the store
store = KVStore()

# Add an entry
store.add("key1", "value1")

# Retrieve an entry
value = store.get("key1")  # Returns "value1"

# Update an entry
store.update("key1", "new_value")

# Delete an entry
store.delete("key1")
```
