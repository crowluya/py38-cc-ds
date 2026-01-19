"""
Unified Hybrid Search API combining BM25, semantic search, and query expansion
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from src.search.base import BaseSearcher
from src.search.preprocessing import TextPreprocessor, QueryPreprocessor
from src.search.bm25 import BM25Searcher
from src.search.semantic import SemanticSearcher
from src.search.expansion import QueryExpander
from src.search.fusion import ResultFusion
from src.models import Document, Query, SearchResult
from src.utils import load_config, setup_logging, ensure_dir


class HybridSearch(BaseSearcher):
    """
    Unified hybrid search engine combining:
    - BM25 keyword search
    - Semantic vector search
    - Query expansion
    """

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize hybrid search engine

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = load_config(config_path)

        # Setup logging
        self.logger = setup_logging(self.config)

        # Initialize preprocessors
        self.doc_preprocessor = TextPreprocessor(self.config)
        self.query_preprocessor = QueryPreprocessor(self.config)

        # Initialize search components
        self.bm25_searcher = BM25Searcher(self.config, self.doc_preprocessor)
        self.semantic_searcher = SemanticSearcher(self.config)
        self.query_expander = QueryExpander(
            self.config,
            self.query_preprocessor,
            self.semantic_searcher.embedding_generator if hasattr(self.semantic_searcher, 'embedding_generator') else None
        )

        # Initialize fusion
        self.fusion = ResultFusion(self.config)

        # Track if indexed
        self.is_indexed = False

        self.logger.info("HybridSearch initialized")

    def index_documents(self, documents: List[Document]) -> None:
        """
        Index documents for all search methods

        Args:
            documents: List of documents to index
        """
        self.logger.info(f"Indexing {len(documents)} documents...")

        # Index with BM25
        self.logger.info("Indexing with BM25...")
        self.bm25_searcher.index_documents(documents)

        # Index with semantic search
        self.logger.info("Indexing with semantic search...")
        self.semantic_searcher.index_documents(documents)

        # Build vocabulary for query expansion
        vocabulary = self._build_vocabulary(documents)
        self.query_expander.set_vocabulary(vocabulary)

        self.is_indexed = True
        self.logger.info("Indexing complete")

    def _build_vocabulary(self, documents: List[Document]) -> List[str]:
        """
        Build vocabulary from documents for query expansion

        Args:
            documents: List of documents

        Returns:
            List of unique terms
        """
        vocabulary = set()

        for doc in documents:
            if doc.tokens:
                vocabulary.update(doc.tokens)
            else:
                tokens = self.doc_preprocessor.preprocess(doc.content)
                vocabulary.update(tokens)

        return list(vocabulary)

    def search(self, query_text: str, k: int = 10, min_score: float = 0.0,
               filters: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """
        Search using hybrid approach

        Args:
            query_text: Search query text
            k: Number of results to return
            min_score: Minimum score threshold
            filters: Optional metadata filters

        Returns:
            List of search results
        """
        if not self.is_indexed:
            self.logger.warning("Search attempted before indexing")
            return []

        # Create query object
        query = Query(
            text=query_text,
            k=k,
            min_score=min_score,
            filters=filters or {}
        )

        # Expand query
        query = self.query_expander.expand(query)

        # Search with different methods
        result_sets = []

        # BM25 search
        bm25_results = self.bm25_searcher.search(query)
        result_sets.append(bm25_results)
        self.logger.debug(f"BM25 found {len(bm25_results)} results")

        # Semantic search
        semantic_results = self.semantic_searcher.search(query)
        result_sets.append(semantic_results)
        self.logger.debug(f"Semantic found {len(semantic_results)} results")

        # Search with expanded query (if expansion occurred)
        if query.expanded_terms:
            expanded_query = Query(
                text=query.text,
                k=k,
                min_score=min_score,
                filters=filters or {}
            )
            expanded_results = self.bm25_searcher.search(expanded_query)
            result_sets.append(expanded_results)
            self.logger.debug(f"Expanded query found {len(expanded_results)} results")

        # Fuse results
        fused_results = self.fusion.fuse(result_sets)

        # Apply filters if provided
        if filters:
            fused_results = self._apply_filters(fused_results, filters)

        # Limit to k results
        fused_results = fused_results[:k]

        self.logger.info(f"Search returned {len(fused_results)} results")

        return fused_results

    def _apply_filters(self, results: List[SearchResult],
                       filters: Dict[str, Any]) -> List[SearchResult]:
        """
        Apply metadata filters to results

        Args:
            results: Search results
            filters: Filter criteria

        Returns:
            Filtered results
        """
        filtered = []

        for result in results:
            match = True
            for key, value in filters.items():
                if key not in result.document.metadata:
                    match = False
                    break

                if result.document.metadata[key] != value:
                    match = False
                    break

            if match:
                filtered.append(result)

        return filtered

    def search_bm25_only(self, query_text: str, k: int = 10,
                        min_score: float = 0.0) -> List[SearchResult]:
        """
        Search using only BM25

        Args:
            query_text: Search query
            k: Number of results
            min_score: Minimum score

        Returns:
            Search results
        """
        query = Query(text=query_text, k=k, min_score=min_score)
        return self.bm25_searcher.search(query)

    def search_semantic_only(self, query_text: str, k: int = 10,
                            min_score: float = 0.0) -> List[SearchResult]:
        """
        Search using only semantic search

        Args:
            query_text: Search query
            k: Number of results
            min_score: Minimum score

        Returns:
            Search results
        """
        query = Query(text=query_text, k=k, min_score=min_score)
        return self.semantic_searcher.search(query)

    def save_index(self, path: str) -> None:
        """
        Save all indices to disk

        Args:
            path: Base path for saving indices
        """
        ensure_dir(path)

        self.logger.info(f"Saving indices to {path}...")

        # Save BM25 index
        self.bm25_searcher.save_index(f"{path}/bm25_index.pkl")

        # Save semantic index
        self.semantic_searcher.save_index(f"{path}/semantic_index")

        self.logger.info("Indices saved")

    def load_index(self, path: str) -> None:
        """
        Load all indices from disk

        Args:
            path: Base path for loading indices
        """
        self.logger.info(f"Loading indices from {path}...")

        # Load BM25 index
        self.bm25_searcher.load_index(f"{path}/bm25_index.pkl")

        # Load semantic index
        self.semantic_searcher.load_index(f"{path}/semantic_index")

        self.is_indexed = True

        self.logger.info("Indices loaded")

    def update_config(self, config_updates: Dict[str, Any]) -> None:
        """
        Update configuration

        Args:
            config_updates: Dictionary of configuration updates
        """
        for key, value in config_updates.items():
            if key in self.config:
                self.config[key] = value

        # Reinitialize components with new config
        self.fusion = ResultFusion(self.config)

        self.logger.info(f"Configuration updated: {list(config_updates.keys())}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get search engine statistics

        Returns:
            Dictionary of statistics
        """
        return {
            'is_indexed': self.is_indexed,
            'document_count': self.bm25_searcher.indexer.document_count(),
            'embedding_dim': self.semantic_searcher.get_embedding_dim(),
            'config': {
                'bm25_k1': self.bm25_searcher.k1,
                'bm25_b': self.bm25_searcher.b,
                'fusion_strategy': self.fusion.fusion_strategy,
                'bm25_weight': self.fusion.bm25_weight,
                'semantic_weight': self.fusion.semantic_weight,
                'expansion_enabled': self.query_expander.enabled
            }
        }


__all__ = ['HybridSearch']
