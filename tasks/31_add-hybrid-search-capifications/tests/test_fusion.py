"""
Tests for score fusion
"""

import pytest
from src.search.fusion import ScoreNormalizer, ResultFusion
from src.models import Document, SearchResult


class TestScoreNormalizer:
    """Test score normalization"""

    def test_min_max_normalize(self):
        """Test min-max normalization"""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        normalized = ScoreNormalizer.min_max_normalize(scores)

        assert len(normalized) == len(scores)
        assert min(normalized) == 0.0
        assert max(normalized) == 1.0

    def test_min_max_normalize_empty(self):
        """Test min-max normalization with empty list"""
        scores = []
        normalized = ScoreNormalizer.min_max_normalize(scores)
        assert normalized == []

    def test_min_max_normalize_identical(self):
        """Test min-max normalization with identical scores"""
        scores = [5.0, 5.0, 5.0]
        normalized = ScoreNormalizer.min_max_normalize(scores)
        assert all(s == 1.0 for s in normalized)

    def test_z_score_normalize(self):
        """Test z-score normalization"""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        normalized = ScoreNormalizer.z_score_normalize(scores)

        assert len(normalized) == len(scores)
        # Mean should be close to 0
        mean = sum(normalized) / len(normalized)
        assert abs(mean) < 0.01

    def test_softmax_normalize(self):
        """Test softmax normalization"""
        scores = [1.0, 2.0, 3.0]
        normalized = ScoreNormalizer.softmax_normalize(scores)

        assert len(normalized) == len(scores)
        # Sum should be close to 1
        total = sum(normalized)
        assert abs(total - 1.0) < 0.01


class TestResultFusion:
    """Test result fusion"""

    @pytest.fixture
    def config(self):
        """Get test configuration"""
        return {
            'hybrid': {
                'fusion_strategy': 'weighted',
                'bm25_weight': 0.4,
                'semantic_weight': 0.6,
                'expansion_weight': 0.2,
                'k': 10,
                'normalize_scores': True
            }
        }

    @pytest.fixture
    def fusion(self, config):
        """Get fusion instance"""
        return ResultFusion(config)

    @pytest.fixture
    def sample_results(self):
        """Create sample search results"""
        docs = [
            Document(id="1", content="Content 1"),
            Document(id="2", content="Content 2"),
            Document(id="3", content="Content 3"),
        ]

        results1 = [
            SearchResult(document=docs[0], score=0.9),
            SearchResult(document=docs[1], score=0.7),
        ]

        results2 = [
            SearchResult(document=docs[1], score=0.8),
            SearchResult(document=docs[2], score=0.6),
        ]

        return [results1, results2]

    def test_weighted_fusion(self, fusion, sample_results):
        """Test weighted fusion"""
        fused = fusion._weighted_fusion(sample_results)

        assert len(fused) > 0
        # Check that results are sorted
        assert fused[0].score >= fused[-1].score if len(fused) > 1 else True

    def test_reciprocal_rank_fusion(self, fusion, sample_results):
        """Test reciprocal rank fusion"""
        # Change strategy to RRF
        fusion.fusion_strategy = 'rrf'

        fused = fusion._reciprocal_rank_fusion(sample_results)

        assert len(fused) > 0

    def test_normalize_scores(self, fusion):
        """Test score normalization in results"""
        docs = [Document(id=str(i), content=f"Content {i}") for i in range(3)]
        results = [
            SearchResult(document=docs[0], score=1.0),
            SearchResult(document=docs[1], score=2.0),
            SearchResult(document=docs[2], score=3.0),
        ]

        normalized = fusion.normalize_scores(results)

        assert min(r.score for r in normalized) == 0.0
        assert max(r.score for r in normalized) == 1.0
