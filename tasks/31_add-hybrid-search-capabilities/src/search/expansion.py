"""
Query expansion using synonyms and related terms
"""

import nltk
from typing import List, Dict, Tuple
from nltk.corpus import wordnet
from src.search.base import BaseQueryExpander
from src.search.preprocessing import TextPreprocessor
from src.models import Query
import numpy as np


class SynonymExpander(BaseQueryExpander):
    """Query expansion using WordNet synonyms"""

    def __init__(self, config: Dict[str, Any], preprocessor: TextPreprocessor):
        """
        Initialize synonym expander

        Args:
            config: Configuration dictionary
            preprocessor: Text preprocessor
        """
        self.config = config
        self.preprocessor = preprocessor
        expansion_config = config.get('expansion', {})

        self.max_synonyms = expansion_config.get('max_synonyms', 3)
        self.use_pos_filtering = expansion_config.get('use_pos_filtering', True)
        self.pos_tags = set(expansion_config.get('pos_tags', ['NN', 'NNS', 'JJ', 'RB']))

        # Download WordNet data
        try:
            nltk.data.find('corpora/wordnet')
        except LookupError:
            nltk.download('wordnet', quiet=True)

    def expand(self, query: Query) -> Query:
        """
        Expand query with synonyms

        Args:
            query: Original query

        Returns:
            Expanded query
        """
        # Get tokens from query
        tokens = self.preprocessor.preprocess(query.text)
        expanded_terms = []

        for token in tokens:
            # Get synonyms for token
            synonyms = self.get_synonyms(token)

            # Add unique synonyms that aren't already in query
            for synonym in synonyms:
                if synonym.lower() not in [t.lower() for t in tokens + expanded_terms]:
                    expanded_terms.append(synonym)

                    if len(expanded_terms) >= self.max_synonyms * len(tokens):
                        break

        # Create expanded query
        if expanded_terms:
            expanded_text = f"{query.text} {' '.join(expanded_terms)}"
            query.expanded_terms = expanded_terms
            query.text = expanded_text

        return query

    def get_synonyms(self, term: str) -> List[str]:
        """
        Get synonyms for a term from WordNet

        Args:
            term: Term to get synonyms for

        Returns:
            List of synonyms
        """
        synonyms = set()

        # Get synsets for the term
        synsets = wordnet.synsets(term)

        for synset in synsets:
            # Filter by POS if enabled
            if self.use_pos_filtering:
                pos = synset.pos()
                # Map WordNet POS to our tags
                pos_map = {
                    'n': 'NN',
                    'v': 'VB',
                    'a': 'JJ',
                    'r': 'RB'
                }
                if pos_map.get(pos, '') not in self.pos_tags:
                    continue

            # Get lemmas (synonyms) from synset
            for lemma in synset.lemmas():
                synonym = lemma.name().replace('_', ' ')

                # Don't include the term itself
                if synonym.lower() != term.lower():
                    synonyms.add(synonym)

        return list(synonyms)[:self.max_synonyms]

    def get_related_terms(self, term: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Get related terms using WordNet similarity

        Args:
            term: Term to find related terms for
            top_k: Number of related terms to return

        Returns:
            List of (related_term, similarity) tuples
        """
        related = []

        # Get synsets for the term
        term_synsets = wordnet.synsets(term)

        if not term_synsets:
            return related

        # For each synset, find related synsets
        for synset in term_synsets[:3]:  # Limit to first 3 synsets
            # Get hypernyms (more general terms)
            for hypernym in synset.hypernyms()[:top_k]:
                for lemma in hypernym.lemmas():
                    related.append((lemma.name(), 0.7))  # Fixed similarity for now

            # Get hyponyms (more specific terms)
            for hyponym in synset.hyponyms()[:top_k]:
                for lemma in hyponym.lemmas():
                    related.append((lemma.name(), 0.6))

        # Remove duplicates and the term itself
        seen = {term.lower()}
        unique_related = []
        for rel_term, sim in related:
            if rel_term.lower() not in seen:
                unique_related.append((rel_term, sim))
                seen.add(rel_term.lower())

        return unique_related[:top_k]


class EmbeddingExpander(BaseQueryExpander):
    """Query expansion using embedding similarity"""

    def __init__(self, config: Dict[str, Any], embedding_generator):
        """
        Initialize embedding-based expander

        Args:
            config: Configuration dictionary
            embedding_generator: EmbeddingGenerator instance
        """
        self.config = config
        self.embedding_generator = embedding_generator
        expansion_config = config.get('expansion', {})

        self.max_related = expansion_config.get('max_related', 2)
        self.similarity_threshold = expansion_config.get('similarity_threshold', 0.7)

        # Build vocabulary from corpus (if available)
        self.vocabulary: List[str] = []
        self.vocab_embeddings: np.ndarray = None

    def set_vocabulary(self, vocabulary: List[str]):
        """
        Set vocabulary for expansion

        Args:
            vocabulary: List of terms
        """
        self.vocabulary = vocabulary
        if vocabulary:
            self.vocab_embeddings = self.embedding_generator.encode_batch(vocabulary)

    def expand(self, query: Query) -> Query:
        """
        Expand query with embedding-similar terms

        Args:
            query: Original query

        Returns:
            Expanded query
        """
        if self.vocab_embeddings is None or len(self.vocabulary) == 0:
            return query

        # Get query tokens
        tokens = self.preprocessor.preprocess(query.text)
        expanded_terms = []

        for token in tokens:
            # Get related terms for token
            related = self.get_related_terms(token, top_k=self.max_related)

            # Add related terms
            for rel_term, similarity in related:
                if similarity >= self.similarity_threshold:
                    if rel_term.lower() not in [t.lower() for t in tokens + expanded_terms]:
                        expanded_terms.append(rel_term)

        # Create expanded query
        if expanded_terms:
            expanded_text = f"{query.text} {' '.join(expanded_terms)}"
            query.expanded_terms.extend(expanded_terms)
            query.text = expanded_text

        return query

    def get_synonyms(self, term: str) -> List[str]:
        """
        Get synonyms using embedding similarity (not implemented for this class)

        Args:
            term: Term to get synonyms for

        Returns:
            Empty list (use get_related_terms instead)
        """
        return []

    def get_related_terms(self, term: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Get related terms using embedding similarity

        Args:
            term: Term to find related terms for
            top_k: Number of related terms to return

        Returns:
            List of (related_term, similarity) tuples
        """
        if self.vocab_embeddings is None:
            return []

        # Get embedding for the term
        term_embedding = self.embedding_generator.encode(term)

        # Calculate cosine similarity with all vocabulary terms
        similarities = np.dot(self.vocab_embeddings, term_embedding) / (
            np.linalg.norm(self.vocab_embeddings, axis=1) * np.linalg.norm(term_embedding) + 1e-8
        )

        # Get top-k most similar terms
        top_indices = np.argsort(similarities)[::-1][:top_k + 1]  # +1 to skip the term itself

        related = []
        for idx in top_indices:
            vocab_term = self.vocabulary[idx]
            similarity = float(similarities[idx])

            # Skip the term itself and very similar terms (likely the same)
            if vocab_term.lower() != term.lower() and similarity < 0.99:
                related.append((vocab_term, similarity))

        return related[:top_k]


class QueryExpander(BaseQueryExpander):
    """Combined query expansion using multiple strategies"""

    def __init__(self, config: Dict[str, Any], preprocessor: TextPreprocessor, embedding_generator=None):
        """
        Initialize query expander

        Args:
            config: Configuration dictionary
            preprocessor: Text preprocessor
            embedding_generator: Optional embedding generator for expansion
        """
        self.config = config
        self.preprocessor = preprocessor
        expansion_config = config.get('expansion', {})

        self.enabled = expansion_config.get('enabled', True)
        self.expansion_sources = expansion_config.get('expansion_sources', ['wordnet', 'embedding'])

        # Initialize expanders based on configuration
        self.expanders = []

        if 'wordnet' in self.expansion_sources:
            self.expanders.append(SynonymExpander(config, preprocessor))

        if 'embedding' in self.expansion_sources and embedding_generator is not None:
            emb_expander = EmbeddingExpander(config, embedding_generator)
            self.expanders.append(emb_expander)
            self.embedding_expander = emb_expander  # Keep reference for vocabulary setting

    def expand(self, query: Query) -> Query:
        """
        Expand query using all configured strategies

        Args:
            query: Original query

        Returns:
            Expanded query
        """
        if not self.enabled:
            return query

        # Save original text
        original_text = query.text
        all_expanded_terms = []

        # Apply each expansion strategy
        for expander in self.expanders:
            expanded_query = expander.expand(query)
            all_expanded_terms.extend(expanded_query.expanded_terms)

            # Reset query text for next expander
            query.text = original_text

        # Combine all expanded terms
        if all_expanded_terms:
            unique_expanded = list(set(all_expanded_terms))
            expanded_text = f"{original_text} {' '.join(unique_expanded)}"
            query.expanded_terms = unique_expanded
            query.text = expanded_text

        return query

    def get_synonyms(self, term: str) -> List[str]:
        """Get synonyms from all expanders"""
        all_synonyms = []
        for expander in self.expanders:
            if hasattr(expander, 'get_synonyms'):
                all_synonyms.extend(expander.get_synonyms(term))
        return list(set(all_synonyms))

    def get_related_terms(self, term: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Get related terms from all expanders"""
        all_related = []
        for expander in self.expanders:
            all_related.extend(expander.get_related_terms(term, top_k))

        # Sort by similarity and deduplicate
        seen = set()
        unique_related = []
        for rel_term, sim in sorted(all_related, key=lambda x: x[1], reverse=True):
            if rel_term.lower() not in seen:
                unique_related.append((rel_term, sim))
                seen.add(rel_term.lower())

        return unique_related[:top_k]

    def set_vocabulary(self, vocabulary: List[str]):
        """Set vocabulary for embedding-based expansion"""
        if hasattr(self, 'embedding_expander'):
            self.embedding_expander.set_vocabulary(vocabulary)


__all__ = ['QueryExpander', 'SynonymExpander', 'EmbeddingExpander']
