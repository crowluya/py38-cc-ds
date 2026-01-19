"""
Abstract base classes for search components
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
import numpy as np
from src.models import Document, Query, SearchResult


class BaseSearcher(ABC):
    """Abstract base class for search components"""

    @abstractmethod
    def index_documents(self, documents: List[Document]) -> None:
        """Index documents for searching"""
        pass

    @abstractmethod
    def search(self, query: Query) -> List[SearchResult]:
        """Search for documents matching the query"""
        pass

    @abstractmethod
    def save_index(self, path: str) -> None:
        """Save index to disk"""
        pass

    @abstractmethod
    def load_index(self, path: str) -> None:
        """Load index from disk"""
        pass


class BasePreprocessor(ABC):
    """Abstract base class for text preprocessing"""

    @abstractmethod
    def preprocess(self, text: str) -> List[str]:
        """Preprocess text and return tokens"""
        pass

    @abstractmethod
    def preprocess_batch(self, texts: List[str]) -> List[List[str]]:
        """Preprocess a batch of texts"""
        pass


class BaseIndexer(ABC):
    """Abstract base class for indexing"""

    @abstractmethod
    def add_document(self, doc: Document) -> None:
        """Add a single document to the index"""
        pass

    @abstractmethod
    def add_documents(self, docs: List[Document]) -> None:
        """Add multiple documents to the index"""
        pass

    @abstractmethod
    def get_document(self, doc_id: str) -> Document:
        """Retrieve a document by ID"""
        pass

    @abstractmethod
    def document_count(self) -> int:
        """Return the number of indexed documents"""
        pass


class BaseScorer(ABC):
    """Abstract base class for scoring"""

    @abstractmethod
    def score(self, query: Query, document: Document) -> float:
        """Score a document against a query"""
        pass

    @abstractmethod
    def score_batch(self, query: Query, documents: List[Document]) -> List[float]:
        """Score multiple documents against a query"""
        pass


class BaseQueryExpander(ABC):
    """Abstract base class for query expansion"""

    @abstractmethod
    def expand(self, query: Query) -> Query:
        """Expand query with additional terms"""
        pass

    @abstractmethod
    def get_synonyms(self, term: str) -> List[str]:
        """Get synonyms for a term"""
        pass

    @abstractmethod
    def get_related_terms(self, term: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Get related terms with similarity scores"""
        pass


class BaseFusion(ABC):
    """Abstract base class for result fusion"""

    @abstractmethod
    def fuse(self, result_sets: List[List[SearchResult]]) -> List[SearchResult]:
        """Fuse multiple result sets into one"""
        pass

    @abstractmethod
    def normalize_scores(self, results: List[SearchResult]) -> List[SearchResult]:
        """Normalize scores to [0, 1] range"""
        pass
