# Hybrid Search System - Architecture

## Overview

The Hybrid Search System combines multiple search strategies to provide improved relevance and recall:

1. **BM25 Keyword Search** - Traditional term-based ranking
2. **Semantic Search** - Vector-based similarity using embeddings
3. **Query Expansion** - Synonym and related term expansion
4. **Score Fusion** - Intelligent combination of multiple signals

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     HybridSearch API                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Query Processing                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Preprocessor │  │   Expander   │  │   Formatter  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  BM25 Searcher  │ │ Semantic Search │ │ Expansion Query │
│                 │ │                 │ │                 │
│ • Term freq     │ │ • Embeddings    │ │ • Synonyms      │
│ • IDF           │ │ • FAISS index   │ │ • Related terms │
│ • Doc length    │ │ • Cosine sim    │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Result Fusion                             │
│  • Score Normalization  • Weighted Combination  • RRF      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Ranked Results                          │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Text Preprocessing

**Location:** `src/search/preprocessing.py`

**Classes:**
- `TextPreprocessor` - Document text preprocessing
- `QueryPreprocessor` - Query text preprocessing (more conservative)

**Features:**
- HTML tag removal
- URL and email removal
- Tokenization
- Stopword removal
- Lemmatization
- Length filtering

### 2. BM25 Search

**Location:** `src/search/bm25.py`

**Classes:**
- `BM25Indexer` - Document indexing
- `BM25Searcher` - Search execution

**Algorithm:**
```
BM25(D,Q) = Σ IDF(qi) × (f(qi,D) × (k1 + 1)) / (f(qi,D) + k1 × (1 - b + b × |D|/avgdl))

Where:
- qi: query term
- f(qi,D): frequency of qi in document D
- |D|: document length
- avgdl: average document length
- k1: term saturation parameter (default: 1.5)
- b: length normalization (default: 0.75)
```

### 3. Semantic Search

**Location:** `src/search/semantic.py`

**Classes:**
- `EmbeddingGenerator` - Generate text embeddings
- `VectorIndex` - FAISS-based vector index
- `SemanticSearcher` - Semantic search execution

**Features:**
- Sentence transformer embeddings (all-MiniLM-L6-v2)
- FAISS indexing for efficient similarity search
- Configurable distance metrics (L2, inner product)
- Embedding caching for performance

### 4. Query Expansion

**Location:** `src/search/expansion.py`

**Classes:**
- `SynonymExpander` - WordNet-based synonym expansion
- `EmbeddingExpander` - Embedding-based related term expansion
- `QueryExpander` - Combined expansion strategy

**Features:**
- WordNet synonym extraction
- Part-of-speech filtering
- Embedding-based related terms
- Configurable expansion limits

### 5. Score Fusion

**Location:** `src/search/fusion.py`

**Classes:**
- `ScoreNormalizer` - Score normalization methods
- `ResultFusion` - Result fusion strategies

**Normalization Methods:**
- Min-max normalization
- Z-score normalization
- Sigmoid normalization
- Softmax normalization

**Fusion Strategies:**
- **Weighted Fusion**: Combine normalized scores with configurable weights
  ```
  score = w1 × BM25 + w2 × Semantic + w3 × Expansion
  ```
- **Reciprocal Rank Fusion (RRF)**: Rank-based fusion
  ```
  score = Σ 1 / (k + ranki)
  ```

## Data Flow

### Indexing Flow

```
Document → Tokenization → BM25 Index
    ↓
Embedding Generation → Vector Index
    ↓
Vocabulary Building → Query Expansion
```

### Search Flow

```
Query → Preprocessing → Expansion → Parallel Search:
                                          ├─ BM25
                                          ├─ Semantic
                                          └─ Expanded Query
                                              ↓
                                          Result Fusion
                                              ↓
                                          Ranked Results
```

## Configuration

All components are configured through `config/config.yaml`:

```yaml
bm25:
  k1: 1.5        # Term saturation
  b: 0.75        # Length normalization

semantic:
  model_name: "all-MiniLM-L6-v2"
  batch_size: 32

hybrid:
  bm25_weight: 0.4
  semantic_weight: 0.6
  fusion_strategy: "weighted"

expansion:
  enabled: true
  max_synonyms: 3
```

## Performance Considerations

### Indexing Performance
- Batch embedding generation (configurable batch size)
- Incremental indexing support
- Index persistence for fast startup

### Query Performance
- Parallel execution of search methods
- Embedding caching
- Efficient FAISS vector search
- Configurable result limits

### Memory Usage
- Embedding cache with configurable size limit
- Disk-based index persistence
- Lazy loading of large indices

## Scalability

### Current Capacity
- **Documents**: Tested with up to 100K documents
- **Query Latency**: <500ms for typical queries
- **Memory**: ~2GB for 100K documents (including embeddings)

### Scaling Options
- For >1M documents:
  - Use FAISS IndexIVFFlat for approximate search
  - Implement distributed indexing
  - Consider Elasticsearch for BM25

## Extensions

### Adding New Search Methods

1. Inherit from `BaseSearcher`
2. Implement `index_documents()` and `search()`
3. Add to fusion in `HybridSearch`

### Custom Fusion Strategies

1. Inherit from `BaseFusion`
2. Implement `fuse()` method
3. Update configuration

### Additional Embedding Models

1. Modify `EmbeddingGenerator`
2. Update config with new model name
3. Reindex if embedding dimension changes
