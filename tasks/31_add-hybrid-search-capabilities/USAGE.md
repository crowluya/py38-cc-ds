# Hybrid Search System - Usage Guide

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd hybrid-search

# Install dependencies
pip install -r requirements.txt

# Download required NLTK data
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"
```

## Quick Start

### Basic Usage

```python
from src.search import HybridSearch
from src.models import Document

# Initialize search engine
search_engine = HybridSearch()

# Create documents
documents = [
    Document(id="1", content="Machine learning is a subset of AI."),
    Document(id="2", content="Deep learning uses neural networks."),
    Document(id="3", content="NLP processes human language."),
]

# Index documents
search_engine.index_documents(documents)

# Search
results = search_engine.search("artificial intelligence", k=3)

# Display results
for result in results:
    print(f"Score: {result.score:.3f}")
    print(f"Content: {result.document.content}\n")
```

## Advanced Usage

### Custom Configuration

```python
# Create custom config
config = {
    'bm25': {'k1': 1.8, 'b': 0.8},
    'semantic': {'model_name': 'all-mpnet-base-v2'},
    'hybrid': {
        'bm25_weight': 0.5,
        'semantic_weight': 0.5,
        'fusion_strategy': 'weighted'
    },
    'expansion': {
        'enabled': True,
        'max_synonyms': 5
    }
}

# Update search engine config
search_engine.update_config(config)
```

### Search with Filters

```python
# Add metadata to documents
documents = [
    Document(
        id="1",
        content="Machine learning article",
        metadata={"category": "AI", "year": 2024}
    ),
    Document(
        id="2",
        content="Deep learning tutorial",
        metadata={"category": "AI", "year": 2023}
    ),
]

# Search with filters
results = search_engine.search(
    "machine learning",
    filters={"category": "AI", "year": 2024}
)
```

### Individual Search Methods

```python
# BM25 only
bm25_results = search_engine.search_bm25_only("query", k=5)

# Semantic only
semantic_results = search_engine.search_semantic_only("query", k=5)

# Hybrid (default)
hybrid_results = search_engine.search("query", k=5)
```

### Save and Load Indices

```python
# Save indices
search_engine.save_index("data/my_index")

# Load indices
search_engine.load_index("data/my_index")
```

## Configuration Options

### BM25 Parameters

```yaml
bm25:
  k1: 1.5    # Term saturation (1.2-2.0)
             # Higher = more term frequency influence
  b: 0.75    # Length normalization (0.0-1.0)
             # Higher = more length normalization
```

**Tuning Guide:**
- Increase k1 for longer queries
- Decrease b for short documents
- Default values work well for most cases

### Semantic Search Parameters

```yaml
semantic:
  model_name: "all-MiniLM-L6-v2"  # Fast, good quality
  # Other options:
  # - "all-mpnet-base-v2" (slower, better quality)
  # - "multi-qa-mpnet-base-dot-v1" (optimized for QA)
  batch_size: 32
  index_type: "IndexFlatL2"  # Exact search
  # Use "IndexIVFFlat" for >100K documents
```

### Hybrid Fusion Parameters

```yaml
hybrid:
  bm25_weight: 0.4      # Weight for keyword search
  semantic_weight: 0.6  # Weight for semantic search
  fusion_strategy: "weighted"  # or "rrf"
```

**Choosing Weights:**
- More BM25 weight for exact keyword matching
- More semantic weight for conceptual similarity
- 50/50 is a good starting point

### Query Expansion Parameters

```yaml
expansion:
  enabled: true
  max_synonyms: 3  # Maximum synonyms per term
  max_related: 2   # Maximum related terms per term
  expansion_sources:
    - "wordnet"    # Synonyms from WordNet
    - "embedding"  # Similar terms from embeddings
```

## Best Practices

### 1. Document Preparation

```python
# Good: Clear, descriptive content
good_doc = Document(
    id="1",
    title="Introduction to Machine Learning",
    content="Machine learning is a branch of artificial intelligence...",
    metadata={"topic": "ML", "level": "beginner"}
)

# Bad: Vague, short content
bad_doc = Document(
    id="2",
    content="ML is AI tech."  # Too short, lacks context
)
```

### 2. Query Formulation

```python
# Good: Natural language queries
query = "how does machine learning work?"

# Good: Specific terms
query = "neural network backpropagation"

# Bad: Too broad
query = "ai"  # Will return many irrelevant results
```

### 3. Performance Optimization

```python
# For large datasets:
config = {
    'semantic': {
        'batch_size': 64,  # Larger batches
        'index_type': 'IndexIVFFlat',  # Approximate search
        'nlist': 100  # Number of clusters
    },
    'performance': {
        'cache_embeddings': True,
        'cache_size_mb': 1000  # Larger cache
    }
}
```

### 4. Index Management

```python
# Incremental indexing
new_docs = [Document(...), Document(...)]
search_engine.index_documents(new_docs)  # Adds to existing index

# Save periodically
search_engine.save_index("data/backup")
```

## Evaluation

### Measuring Search Quality

```python
# Get detailed scores
results = search_engine.search("query")

for result in results:
    print(f"BM25 Score: {result.bm25_score:.3f}")
    print(f"Semantic Score: {result.semantic_score:.3f}")
    print(f"Combined Score: {result.score:.3f}")
```

### Comparing Methods

```python
query = "test query"

bm25 = search_engine.search_bm25_only(query)
semantic = search_engine.search_semantic_only(query)
hybrid = search_engine.search(query)

print(f"BM25 results: {len(bm25)}")
print(f"Semantic results: {len(semantic)}")
print(f"Hybrid results: {len(hybrid)}")
```

## Troubleshooting

### No Results Returned

**Possible causes:**
- Score threshold too high
- No documents indexed
- Query terms not in vocabulary

**Solutions:**
```python
# Lower score threshold
results = search_engine.search("query", min_score=0.0)

# Check index status
stats = search_engine.get_stats()
print(stats)
```

### Slow Queries

**Possible causes:**
- Large dataset with exact search
- No embedding caching
- Small batch size

**Solutions:**
```python
# Use approximate search
config = {'semantic': {'index_type': 'IndexIVFFlat'}}
search_engine.update_config(config)

# Increase cache
config = {'performance': {'cache_size_mb': 1000}}
search_engine.update_config(config)
```

### Poor Relevance

**Possible causes:**
- Weights not tuned for your data
- Wrong embedding model
- Query expansion too aggressive

**Solutions:**
```python
# Adjust weights
config = {
    'hybrid': {
        'bm25_weight': 0.6,  # More keyword matching
        'semantic_weight': 0.4
    }
}
search_engine.update_config(config)

# Disable expansion
config = {'expansion': {'enabled': False}}
search_engine.update_config(config)
```

## Examples

See `example.py` for complete working examples including:
- Document indexing
- Various search queries
- Method comparison
- Performance evaluation
