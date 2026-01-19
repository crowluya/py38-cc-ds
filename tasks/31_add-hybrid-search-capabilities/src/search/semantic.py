"""
Semantic search using vector embeddings
"""

import pickle
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import faiss
from src.search.base import BaseSearcher
from src.models import Document, Query, SearchResult


class EmbeddingGenerator:
    """Generate embeddings for text using sentence transformers"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize embedding generator

        Args:
            config: Configuration dictionary
        """
        self.config = config
        semantic_config = config.get('semantic', {})
        self.model_name = semantic_config.get('model_name', 'all-MiniLM-L6-v2')
        self.batch_size = semantic_config.get('batch_size', 32)
        self.max_length = semantic_config.get('max_length', 512)

        # Load model
        self.model = SentenceTransformer(self.model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

        # Embedding cache
        self.embedding_cache: Dict[str, np.ndarray] = {}
        self.cache_enabled = config.get('performance', {}).get('cache_embeddings', True)

    def encode(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        if self.cache_enabled and text in self.embedding_cache:
            return self.embedding_cache[text]

        embedding = self.model.encode(
            text,
            show_progress_bar=False,
            convert_to_numpy=True
        )

        if self.cache_enabled:
            self.embedding_cache[text] = embedding

        return embedding

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of input texts

        Returns:
            Array of embedding vectors
        """
        # Check cache
        cached_embeddings = []
        uncached_texts = []
        uncached_indices = []

        for i, text in enumerate(texts):
            if self.cache_enabled and text in self.embedding_cache:
                cached_embeddings.append((i, self.embedding_cache[text]))
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Encode uncached texts
        if uncached_texts:
            new_embeddings = self.model.encode(
                uncached_texts,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True
            )

            # Cache new embeddings
            if self.cache_enabled:
                for text, embedding in zip(uncached_texts, new_embeddings):
                    self.embedding_cache[text] = embedding
        else:
            new_embeddings = []

        # Combine cached and new embeddings
        embeddings = np.zeros((len(texts), self.embedding_dim))
        for i, emb in cached_embeddings:
            embeddings[i] = emb
        for i, emb in zip(uncached_indices, new_embeddings):
            embeddings[i] = emb

        return embeddings

    def get_embedding_dim(self) -> int:
        """Get the embedding dimension"""
        return self.embedding_dim

    def clear_cache(self):
        """Clear the embedding cache"""
        self.embedding_cache.clear()


class VectorIndex:
    """FAISS vector index for efficient similarity search"""

    def __init__(self, embedding_dim: int, config: Dict[str, Any]):
        """
        Initialize vector index

        Args:
            embedding_dim: Dimension of embeddings
            config: Configuration dictionary
        """
        self.embedding_dim = embedding_dim
        self.config = config
        semantic_config = config.get('semantic', {})
        self.index_type = semantic_config.get('index_type', 'IndexFlatL2')

        # Initialize FAISS index
        if self.index_type == 'IndexFlatL2':
            # Exact search with L2 distance
            self.index = faiss.IndexFlatL2(embedding_dim)
        elif self.index_type == 'IndexFlatIP':
            # Exact search with inner product (cosine similarity if normalized)
            self.index = faiss.IndexFlatIP(embedding_dim)
        elif self.index_type == 'IndexIVFFlat':
            # Approximate search with IVF
            nlist = semantic_config.get('nlist', 100)
            quantizer = faiss.IndexFlatL2(embedding_dim)
            self.index = faiss.IndexIVFFlat(quantizer, embedding_dim, nlist)
        else:
            # Default to IndexFlatL2
            self.index = faiss.IndexFlatL2(embedding_dim)

        # Document IDs mapping
        self.doc_ids: List[str] = []
        self.is_trained = False

    def add_vectors(self, vectors: np.ndarray, doc_ids: List[str]) -> None:
        """
        Add vectors to the index

        Args:
            vectors: Array of vectors to add
            doc_ids: Corresponding document IDs
        """
        if not self.is_trained and self.index_type == 'IndexIVFFlat':
            # Train IVF index if needed
            self.index.train(vectors)
            self.is_trained = True

        # Add vectors to index
        start_idx = len(self.doc_ids)
        self.index.add(vectors.astype('float32'))
        self.doc_ids.extend(doc_ids)

    def search(self, query_vector: np.ndarray, k: int = 10) -> tuple:
        """
        Search for similar vectors

        Args:
            query_vector: Query vector
            k: Number of results to return

        Returns:
            Tuple of (distances, indices)
        """
        if len(self.doc_ids) == 0:
            return np.array([]), np.array([])

        # Ensure query vector is 2D
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)

        distances, indices = self.index.search(query_vector.astype('float32'), k)

        return distances[0], indices[0]

    def get_doc_ids(self) -> List[str]:
        """Get all document IDs in the index"""
        return self.doc_ids

    def save_index(self, path: str) -> None:
        """
        Save index to disk

        Args:
            path: Path to save index
        """
        faiss.write_index(self.index, f"{path}.index")

        # Save metadata
        metadata = {
            'doc_ids': self.doc_ids,
            'embedding_dim': self.embedding_dim,
            'is_trained': self.is_trained
        }
        with open(f"{path}.meta", 'wb') as f:
            pickle.dump(metadata, f)

    def load_index(self, path: str) -> None:
        """
        Load index from disk

        Args:
            path: Path to load index from
        """
        self.index = faiss.read_index(f"{path}.index")

        # Load metadata
        with open(f"{path}.meta", 'rb') as f:
            metadata = pickle.load(f)

        self.doc_ids = metadata['doc_ids']
        self.embedding_dim = metadata['embedding_dim']
        self.is_trained = metadata.get('is_trained', True)


class SemanticSearcher(BaseSearcher):
    """Semantic search using vector embeddings"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize semantic searcher

        Args:
            config: Configuration dictionary
        """
        self.config = config

        # Initialize embedding generator
        self.embedding_generator = EmbeddingGenerator(config)

        # Initialize vector index
        self.vector_index = VectorIndex(
            self.embedding_generator.get_embedding_dim(),
            config
        )

        # Store documents for retrieval
        self.documents: Dict[str, Document] = {}

    def index_documents(self, documents: List[Document]) -> None:
        """
        Index documents for semantic searching

        Args:
            documents: List of documents to index
        """
        if not documents:
            return

        # Generate embeddings
        texts = [doc.content for doc in documents]
        embeddings = self.embedding_generator.encode_batch(texts)

        # Add to vector index
        doc_ids = [doc.id for doc in documents]
        self.vector_index.add_vectors(embeddings, doc_ids)

        # Store documents with embeddings
        for doc, embedding in zip(documents, embeddings):
            doc.embedding = embedding
            self.documents[doc.id] = doc

    def search(self, query: Query) -> List[SearchResult]:
        """
        Search for documents using semantic similarity

        Args:
            query: Search query

        Returns:
            List of search results
        """
        if len(self.vector_index.get_doc_ids()) == 0:
            return []

        # Generate query embedding
        query_embedding = self.embedding_generator.encode(query.text)

        # Search vector index
        k = min(query.k, len(self.vector_index.get_doc_ids()))
        distances, indices = self.vector_index.search(query_embedding, k)

        # Convert distances to similarities (for L2 distance, we use negative distance)
        # For cosine similarity, you would use the actual similarity score
        results = []
        for distance, idx in zip(distances, indices):
            if idx == -1:  # FAISS returns -1 for missing results
                continue

            doc_id = self.vector_index.get_doc_ids()[idx]
            doc = self.documents.get(doc_id)

            if doc and distance < float('inf'):
                # Convert L2 distance to similarity score
                # Lower distance = higher similarity
                similarity = 1.0 / (1.0 + float(distance))

                if similarity >= query.min_score:
                    result = SearchResult(
                        document=doc,
                        score=similarity,
                        semantic_score=similarity
                    )
                    results.append(result)

        # Sort by score
        results.sort(reverse=True)

        return results

    def save_index(self, path: str) -> None:
        """
        Save index to disk

        Args:
            path: Path to save index
        """
        self.vector_index.save_index(path)

        # Save documents
        with open(f"{path}.docs", 'wb') as f:
            pickle.dump(self.documents, f)

    def load_index(self, path: str) -> None:
        """
        Load index from disk

        Args:
            path: Path to load index from
        """
        self.vector_index.load_index(path)

        # Load documents
        with open(f"{path}.docs", 'rb') as f:
            self.documents = pickle.load(f)

    def get_embedding_dim(self) -> int:
        """Get the embedding dimension"""
        return self.embedding_generator.get_embedding_dim()


__all__ = ['SemanticSearcher', 'EmbeddingGenerator', 'VectorIndex']
