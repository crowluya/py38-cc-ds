"""
Tests for data models
"""

import pytest
import numpy as np
from src.models import Document, SearchResult, Query, SearchConfig


class TestDocument:
    """Test Document model"""

    def test_create_document(self):
        """Test creating a document"""
        doc = Document(
            id="1",
            content="Test content",
            title="Test Title"
        )
        assert doc.id == "1"
        assert doc.content == "Test content"
        assert doc.title == "Test Title"
        assert doc.metadata == {}

    def test_document_with_embedding(self):
        """Test document with embedding"""
        embedding = np.array([0.1, 0.2, 0.3])
        doc = Document(
            id="1",
            content="Test",
            embedding=embedding
        )
        assert doc.embedding is not None
        assert isinstance(doc.embedding, np.ndarray)

    def test_document_with_metadata(self):
        """Test document with metadata"""
        doc = Document(
            id="1",
            content="Test",
            metadata={"category": "tech", "date": "2024-01-01"}
        )
        assert doc.metadata["category"] == "tech"
        assert doc.metadata["date"] == "2024-01-01"


class TestSearchResult:
    """Test SearchResult model"""

    def test_create_search_result(self):
        """Test creating a search result"""
        doc = Document(id="1", content="Test")
        result = SearchResult(
            document=doc,
            score=0.95
        )
        assert result.document.id == "1"
        assert result.score == 0.95

    def test_search_result_comparison(self):
        """Test search result sorting"""
        doc1 = Document(id="1", content="Test 1")
        doc2 = Document(id="2", content="Test 2")

        result1 = SearchResult(document=doc1, score=0.7)
        result2 = SearchResult(document=doc2, score=0.9)

        results = [result1, result2]
        results.sort()

        assert results[0].score > results[1].score


class TestQuery:
    """Test Query model"""

    def test_create_query(self):
        """Test creating a query"""
        query = Query(text="test query")
        assert query.text == "test query"
        assert query.original_text == "test query"
        assert query.k == 10

    def test_query_with_expansion(self):
        """Test query with expanded terms"""
        query = Query(
            text="test query",
            expanded_terms=["exam", "check"]
        )
        assert len(query.expanded_terms) == 2
        assert "exam" in query.expanded_terms


class TestSearchConfig:
    """Test SearchConfig model"""

    def test_default_config(self):
        """Test default configuration"""
        config = SearchConfig()
        assert config.bm25_k1 == 1.5
        assert config.bm25_b == 0.75
        assert config.bm25_weight == 0.4
        assert config.semantic_weight == 0.6

    def test_custom_config(self):
        """Test custom configuration"""
        config = SearchConfig(
            bm25_k1=2.0,
            semantic_weight=0.7
        )
        assert config.bm25_k1 == 2.0
        assert config.semantic_weight == 0.7
