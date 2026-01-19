"""
BM25 keyword search implementation
"""

import pickle
import numpy as np
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
from scipy.sparse import csr_matrix
from src.search.base import BaseSearcher, BaseIndexer
from src.search.preprocessing import TextPreprocessor
from src.models import Document, Query, SearchResult


class BM25Indexer(BaseIndexer):
    """BM25 document indexer"""

    def __init__(self, preprocessor: TextPreprocessor):
        """
        Initialize BM25 indexer

        Args:
            preprocessor: Text preprocessor instance
        """
        self.preprocessor = preprocessor
        self.documents: Dict[str, Document] = {}
        self.tokenized_corpus: List[List[str]] = []
        self.doc_ids: List[str] = []
        self.doc_lengths: Dict[str, int] = {}
        self.avg_doc_length = 0.0

    def add_document(self, doc: Document) -> None:
        """Add a single document to the index"""
        if doc.id in self.documents:
            return

        # Preprocess document content
        tokens = self.preprocessor.preprocess(doc.content)
        doc.tokens = tokens

        # Store document
        self.documents[doc.id] = doc
        self.doc_ids.append(doc.id)
        self.tokenized_corpus.append(tokens)
        self.doc_lengths[doc.id] = len(tokens)

        # Update average document length
        self._update_avg_length()

    def add_documents(self, docs: List[Document]) -> None:
        """Add multiple documents to the index"""
        for doc in docs:
            self.add_document(doc)

    def _update_avg_length(self):
        """Update average document length"""
        if self.doc_lengths:
            self.avg_doc_length = sum(self.doc_lengths.values()) / len(self.doc_lengths)

    def get_document(self, doc_id: str) -> Document:
        """Retrieve a document by ID"""
        return self.documents.get(doc_id)

    def document_count(self) -> int:
        """Return the number of indexed documents"""
        return len(self.documents)

    def get_tokenized_corpus(self) -> List[List[str]]:
        """Get the tokenized corpus"""
        return self.tokenized_corpus

    def get_doc_ids(self) -> List[str]:
        """Get list of document IDs"""
        return self.doc_ids

    def clear(self):
        """Clear the index"""
        self.documents.clear()
        self.tokenized_corpus.clear()
        self.doc_ids.clear()
        self.doc_lengths.clear()
        self.avg_doc_length = 0.0


class BM25Searcher(BaseSearcher):
    """BM25 search implementation"""

    def __init__(self, config: Dict[str, Any], preprocessor: TextPreprocessor):
        """
        Initialize BM25 searcher

        Args:
            config: Configuration dictionary
            preprocessor: Text preprocessor instance
        """
        self.config = config
        self.preprocessor = preprocessor

        # BM25 parameters
        bm25_config = config.get('bm25', {})
        self.k1 = bm25_config.get('k1', 1.5)
        self.b = bm25_config.get('b', 0.75)
        self.epsilon = bm25_config.get('epsilon', 0.25)

        # Initialize indexer
        self.indexer = BM25Indexer(preprocessor)

        # BM25 model (initialized during indexing)
        self.bm25_model = None

    def index_documents(self, documents: List[Document]) -> None:
        """
        Index documents for BM25 searching

        Args:
            documents: List of documents to index
        """
        # Add documents to indexer
        self.indexer.add_documents(documents)

        # Initialize BM25 model with tokenized corpus
        if self.indexer.get_tokenized_corpus():
            self.bm25_model = BM25Okapi(
                self.indexer.get_tokenized_corpus(),
                k1=self.k1,
                b=self.b,
                epsilon=self.epsilon
            )

    def search(self, query: Query) -> List[SearchResult]:
        """
        Search for documents using BM25

        Args:
            query: Search query

        Returns:
            List of search results
        """
        if self.bm25_model is None:
            return []

        # Preprocess query
        query_tokens = self.preprocessor.preprocess(query.text)

        if not query_tokens:
            return []

        # Get BM25 scores
        scores = self.bm25_model.get_scores(query_tokens)

        # Create search results
        results = []
        for doc_id, score in zip(self.indexer.get_doc_ids(), scores):
            if score > query.min_score:
                doc = self.indexer.get_document(doc_id)
                if doc:
                    result = SearchResult(
                        document=doc,
                        score=float(score),
                        bm25_score=float(score)
                    )
                    results.append(result)

        # Sort by score
        results.sort(reverse=True)

        # Return top k results
        return results[:query.k]

    def get_batch_scores(self, queries: List[Query]) -> List[List[SearchResult]]:
        """
        Get scores for multiple queries

        Args:
            queries: List of queries

        Returns:
            List of search result lists
        """
        return [self.search(query) for query in queries]

    def save_index(self, path: str) -> None:
        """
        Save index to disk

        Args:
            path: Path to save index
        """
        index_data = {
            'documents': self.indexer.documents,
            'tokenized_corpus': self.indexer.tokenized_corpus,
            'doc_ids': self.indexer.doc_ids,
            'doc_lengths': self.indexer.doc_lengths,
            'avg_doc_length': self.indexer.avg_doc_length,
            'k1': self.k1,
            'b': self.b,
            'epsilon': self.epsilon
        }

        with open(path, 'wb') as f:
            pickle.dump(index_data, f)

    def load_index(self, path: str) -> None:
        """
        Load index from disk

        Args:
            path: Path to load index from
        """
        with open(path, 'rb') as f:
            index_data = pickle.load(f)

        # Restore indexer state
        self.indexer.documents = index_data['documents']
        self.indexer.tokenized_corpus = index_data['tokenized_corpus']
        self.indexer.doc_ids = index_data['doc_ids']
        self.indexer.doc_lengths = index_data['doc_lengths']
        self.indexer.avg_doc_length = index_data['avg_doc_length']

        # Restore parameters
        self.k1 = index_data['k1']
        self.b = index_data['b']
        self.epsilon = index_data['epsilon']

        # Reinitialize BM25 model
        if self.indexer.get_tokenized_corpus():
            self.bm25_model = BM25Okapi(
                self.indexer.get_tokenized_corpus(),
                k1=self.k1,
                b=self.b,
                epsilon=self.epsilon
            )

    def get_document_frequency(self, term: str) -> int:
        """
        Get document frequency for a term

        Args:
            term: Term to look up

        Returns:
            Number of documents containing the term
        """
        if self.bm25_model is None:
            return 0

        term = term.lower()
        count = 0
        for doc_tokens in self.indexer.get_tokenized_corpus():
            if term in doc_tokens:
                count += 1
        return count

    def get_idf(self, term: str) -> float:
        """
        Get IDF score for a term

        Args:
            term: Term to look up

        Returns:
            IDF score
        """
        if self.bm25_model is None:
            return 0.0

        df = self.get_document_frequency(term)
        N = self.indexer.document_count()
        if df == 0:
            return 0.0
        return np.log((N - df + 0.5) / (df + 0.5))


__all__ = ['BM25Searcher', 'BM25Indexer']
