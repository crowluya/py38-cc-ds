"""
Score normalization and result fusion for hybrid search
"""

from typing import List, Dict, Tuple
import numpy as np
from src.search.base import BaseFusion
from src.models import SearchResult, Document


class ScoreNormalizer:
    """Normalize scores to different scales"""

    @staticmethod
    def min_max_normalize(scores: List[float]) -> List[float]:
        """
        Min-max normalization to [0, 1] range

        Args:
            scores: List of scores

        Returns:
            Normalized scores
        """
        if not scores:
            return []

        scores_array = np.array(scores)
        min_score = np.min(scores_array)
        max_score = np.max(scores_array)

        if max_score == min_score:
            return [1.0] * len(scores)

        normalized = (scores_array - min_score) / (max_score - min_score)
        return normalized.tolist()

    @staticmethod
    def z_score_normalize(scores: List[float]) -> List[float]:
        """
        Z-score normalization (standardization)

        Args:
            scores: List of scores

        Returns:
            Normalized scores
        """
        if not scores or len(scores) < 2:
            return scores if scores else []

        scores_array = np.array(scores)
        mean = np.mean(scores_array)
        std = np.std(scores_array)

        if std == 0:
            return [0.0] * len(scores)

        normalized = (scores_array - mean) / std
        return normalized.tolist()

    @staticmethod
    def sigmoid_normalize(scores: List[float]) -> List[float]:
        """
        Sigmoid normalization to [0, 1] range

        Args:
            scores: List of scores

        Returns:
            Normalized scores
        """
        if not scores:
            return []

        scores_array = np.array(scores)
        normalized = 1 / (1 + np.exp(-scores_array))
        return normalized.tolist()

    @staticmethod
    def softmax_normalize(scores: List[float]) -> List[float]:
        """
        Softmax normalization (sum to 1)

        Args:
            scores: List of scores

        Returns:
            Normalized scores
        """
        if not scores:
            return []

        scores_array = np.array(scores)
        # Subtract max for numerical stability
        scores_array = scores_array - np.max(scores_array)
        exp_scores = np.exp(scores_array)
        normalized = exp_scores / np.sum(exp_scores)
        return normalized.tolist()


class ResultFusion(BaseFusion):
    """Fuse multiple result sets into one"""

    def __init__(self, config: Dict):
        """
        Initialize result fusion

        Args:
            config: Configuration dictionary
        """
        self.config = config
        hybrid_config = config.get('hybrid', {})

        self.fusion_strategy = hybrid_config.get('fusion_strategy', 'weighted')
        self.normalize_scores = hybrid_config.get('normalize_scores', True)

        # Weights for different components
        self.bm25_weight = hybrid_config.get('bm25_weight', 0.4)
        self.semantic_weight = hybrid_config.get('semantic_weight', 0.6)
        self.expansion_weight = hybrid_config.get('expansion_weight', 0.2)

        # RRF parameter
        self.k_rrf = hybrid_config.get('k', 10)

        self.normalizer = ScoreNormalizer()

    def normalize_scores(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Normalize scores in search results

        Args:
            results: List of search results

        Returns:
            Results with normalized scores
        """
        if not results:
            return results

        # Extract scores
        scores = [result.score for result in results]

        # Normalize scores
        normalized_scores = self.normalizer.min_max_normalize(scores)

        # Update results with normalized scores
        for result, norm_score in zip(results, normalized_scores):
            result.score = norm_score

        return results

    def fuse(self, result_sets: List[List[SearchResult]]) -> List[SearchResult]:
        """
        Fuse multiple result sets into one

        Args:
            result_sets: List of result sets from different searchers

        Returns:
            Fused results
        """
        if not result_sets:
            return []

        if len(result_sets) == 1:
            return result_sets[0]

        if self.fusion_strategy == 'weighted':
            return self._weighted_fusion(result_sets)
        elif self.fusion_strategy == 'rrf':
            return self._reciprocal_rank_fusion(result_sets)
        else:
            return self._weighted_fusion(result_sets)

    def _weighted_fusion(self, result_sets: List[List[SearchResult]]) -> List[SearchResult]:
        """
        Weighted fusion of multiple result sets

        Args:
            result_sets: List of result sets

        Returns:
            Fused results
        """
        # Define weights for each result set
        # Assuming: [BM25 results, Semantic results, Expansion results]
        weights = [self.bm25_weight, self.semantic_weight, self.expansion_weight]
        weights = weights[:len(result_sets)]  # Adjust to actual number of result sets

        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]

        # Collect all documents
        fused_results: Dict[str, SearchResult] = {}

        for results, weight in zip(result_sets, weights):
            # Normalize scores if enabled
            if self.normalize_scores:
                results = self.normalize_scores(results.copy())

            for result in results:
                doc_id = result.document.id

                if doc_id not in fused_results:
                    # Create new result
                    fused_results[doc_id] = SearchResult(
                        document=result.document,
                        score=result.score * weight,
                        bm25_score=result.bm25_score,
                        semantic_score=result.semantic_score,
                        expansion_score=result.expansion_score
                    )
                else:
                    # Add to existing result
                    fused_results[doc_id].score += result.score * weight

                    # Update component scores
                    if result.bm25_score > 0:
                        fused_results[doc_id].bm25_score = result.bm25_score
                    if result.semantic_score > 0:
                        fused_results[doc_id].semantic_score = result.semantic_score
                    if result.expansion_score > 0:
                        fused_results[doc_id].expansion_score = result.expansion_score

        # Convert to list and sort
        results_list = list(fused_results.values())
        results_list.sort(key=lambda x: x.score, reverse=True)

        return results_list

    def _reciprocal_rank_fusion(self, result_sets: List[List[SearchResult]]) -> List[SearchResult]:
        """
        Reciprocal Rank Fusion (RRF) of multiple result sets

        Args:
            result_sets: List of result sets

        Returns:
            Fused results
        """
        # Collect scores for each document
        rrf_scores: Dict[str, float] = {}
        documents: Dict[str, Document] = {}

        for results in result_sets:
            for rank, result in enumerate(results, start=1):
                doc_id = result.document.id

                # RRF formula: 1 / (k + rank)
                rrf_score = 1.0 / (self.k_rrf + rank)

                if doc_id not in rrf_scores:
                    rrf_scores[doc_id] = rrf_score
                    documents[doc_id] = result.document
                else:
                    rrf_scores[doc_id] += rrf_score

        # Create result list
        fused_results = []
        for doc_id, score in rrf_scores.items():
            result = SearchResult(
                document=documents[doc_id],
                score=score
            )
            fused_results.append(result)

        # Sort by score
        fused_results.sort(key=lambda x: x.score, reverse=True)

        return fused_results

    def combine_scores(self, bm25_score: float, semantic_score: float,
                      expansion_score: float = 0.0) -> float:
        """
        Combine individual component scores into a single score

        Args:
            bm25_score: BM25 component score
            semantic_score: Semantic component score
            expansion_score: Expansion component score

        Returns:
            Combined score
        """
        combined = (
            self.bm25_weight * bm25_score +
            self.semantic_weight * semantic_score +
            self.expansion_weight * expansion_score
        )
        return combined


__all__ = ['ScoreNormalizer', 'ResultFusion']
