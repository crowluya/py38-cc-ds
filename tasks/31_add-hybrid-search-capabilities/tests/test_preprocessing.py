"""
Tests for text preprocessing
"""

import pytest
from src.search.preprocessing import TextPreprocessor, QueryPreprocessor


class TestTextPreprocessor:
    """Test text preprocessing"""

    @pytest.fixture
    def config(self):
        """Get test configuration"""
        return {
            'preprocessing': {
                'lowercase': True,
                'remove_stopwords': True,
                'remove_punctuation': True,
                'lemmatize': True,
                'min_word_length': 2,
                'max_word_length': 50
            }
        }

    @pytest.fixture
    def preprocessor(self, config):
        """Get preprocessor instance"""
        return TextPreprocessor(config)

    def test_preprocess_simple_text(self, preprocessor):
        """Test preprocessing simple text"""
        text = "This is a simple test."
        tokens = preprocessor.preprocess(text)
        assert isinstance(tokens, list)
        assert len(tokens) > 0
        assert 'simple' in tokens or 'test' in tokens

    def test_preprocess_empty_text(self, preprocessor):
        """Test preprocessing empty text"""
        text = ""
        tokens = preprocessor.preprocess(text)
        assert tokens == []

    def test_preprocess_with_html(self, preprocessor):
        """Test HTML removal"""
        text = "<p>This is <b>bold</b> text</p>"
        tokens = preprocessor.preprocess(text)
        assert '<p>' not in tokens
        assert '<b>' not in tokens

    def test_preprocess_batch(self, preprocessor):
        """Test batch preprocessing"""
        texts = ["First text", "Second text"]
        results = preprocessor.preprocess_batch(texts)
        assert len(results) == 2
        assert all(isinstance(tokens, list) for tokens in results)

    def test_filter_tokens_by_length(self, preprocessor):
        """Test token length filtering"""
        text = "I am a test"
        tokens = preprocessor.preprocess(text)
        # Short tokens like 'I', 'am' should be filtered out
        assert 'I' not in tokens
        assert 'am' not in tokens


class TestQueryPreprocessor:
    """Test query preprocessing"""

    @pytest.fixture
    def config(self):
        """Get test configuration"""
        return {
            'preprocessing': {
                'lowercase': True,
                'remove_stopwords': True,
                'remove_punctuation': True,
                'lemmatize': True,
                'min_word_length': 2,
                'max_word_length': 50
            }
        }

    @pytest.fixture
    def query_preprocessor(self, config):
        """Get query preprocessor instance"""
        return QueryPreprocessor(config)

    def test_preprocess_query(self, query_preprocessor):
        """Test query preprocessing"""
        query = "machine learning algorithms"
        tokens = query_preprocessor.preprocess(query)
        assert isinstance(tokens, list)
        assert len(tokens) > 0
