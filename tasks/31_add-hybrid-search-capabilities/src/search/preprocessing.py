"""
Text preprocessing pipeline for document and query processing
"""

import re
import string
from typing import List, Dict, Any
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer, PorterStemmer
from src.search.base import BasePreprocessor


class TextPreprocessor(BasePreprocessor):
    """Text preprocessing pipeline with configurable options"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the text preprocessor

        Args:
            config: Preprocessing configuration dictionary
        """
        self.config = config.get('preprocessing', {})
        self.lowercase = self.config.get('lowercase', True)
        self.remove_stopwords = self.config.get('remove_stopwords', True)
        self.remove_punctuation = self.config.get('remove_punctuation', True)
        self.lemmatize = self.config.get('lemmatize', True)
        self.min_word_length = self.config.get('min_word_length', 2)
        self.max_word_length = self.config.get('max_word_length', 50)

        # Download required NLTK data
        self._download_nltk_data()

        # Initialize components
        self.lemmatizer = WordNetLemmatizer()
        self.stemmer = PorterStemmer()
        self.stop_words = set(stopwords.words('english')) if self.remove_stopwords else set()

    def _download_nltk_data(self):
        """Download required NLTK data"""
        required_data = ['punkt', 'stopwords', 'wordnet', 'averaged_perceptron_tagger']
        for data in required_data:
            try:
                nltk.data.find(f'tokenizers/{data}')
            except LookupError:
                try:
                    nltk.download(data, quiet=True)
                except:
                    pass

    def preprocess(self, text: str) -> List[str]:
        """
        Preprocess a single text and return tokens

        Args:
            text: Input text to preprocess

        Returns:
            List of preprocessed tokens
        """
        if not text:
            return []

        # Remove HTML tags
        text = self._remove_html(text)

        # Lowercase
        if self.lowercase:
            text = text.lower()

        # Remove URLs and email addresses
        text = self._remove_urls(text)
        text = self._remove_emails(text)

        # Remove punctuation (but keep some for phrase queries)
        if self.remove_punctuation:
            # Keep apostrophes and hyphens for now
            text = re.sub(r"[^\w\s'-]", " ", text)

        # Tokenize
        tokens = word_tokenize(text)

        # Filter tokens
        tokens = self._filter_tokens(tokens)

        return tokens

    def preprocess_batch(self, texts: List[str]) -> List[List[str]]:
        """
        Preprocess a batch of texts

        Args:
            texts: List of input texts

        Returns:
            List of token lists
        """
        return [self.preprocess(text) for text in texts]

    def _remove_html(self, text: str) -> str:
        """Remove HTML tags from text"""
        clean = re.compile('<.*?>')
        return re.sub(clean, ' ', text)

    def _remove_urls(self, text: str) -> str:
        """Remove URLs from text"""
        url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|'
                                r'[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        return url_pattern.sub('', text)

    def _remove_emails(self, text: str) -> str:
        """Remove email addresses from text"""
        email_pattern = re.compile(r'\S+@\S+')
        return email_pattern.sub('', text)

    def _filter_tokens(self, tokens: List[str]) -> List[str]:
        """
        Filter tokens based on various criteria

        Args:
            tokens: List of tokens to filter

        Returns:
            Filtered list of tokens
        """
        filtered = []

        for token in tokens:
            # Remove standalone punctuation
            if token in string.punctuation:
                continue

            # Remove stopwords
            if token in self.stop_words:
                continue

            # Filter by length
            if len(token) < self.min_word_length or len(token) > self.max_word_length:
                continue

            # Keep only alphabetic tokens (optional - you may want to keep numbers)
            if not token.isalpha():
                continue

            # Lemmatize or stem
            if self.lemmatize:
                token = self.lemmatizer.lemmatize(token)
            else:
                token = self.stemmer.stem(token)

            filtered.append(token)

        return filtered

    def get_pos_tags(self, text: str) -> List[tuple]:
        """
        Get part-of-speech tags for text

        Args:
            text: Input text

        Returns:
            List of (token, pos_tag) tuples
        """
        tokens = word_tokenize(text)
        return nltk.pos_tag(tokens)

    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
        Extract important keywords from text (simple frequency-based)

        Args:
            text: Input text
            top_n: Number of top keywords to return

        Returns:
            List of keywords
        """
        tokens = self.preprocess(text)
        freq_dist = nltk.FreqDist(tokens)
        return [word for word, _ in freq_dist.most_common(top_n)]


class QueryPreprocessor(TextPreprocessor):
    """Preprocessor specifically for queries"""

    def preprocess(self, text: str) -> List[str]:
        """
        Preprocess query text - more conservative than document preprocessing

        Args:
            text: Query text

        Returns:
            List of tokens
        """
        if not text:
            return []

        # Don't lowercase for queries (might be case-sensitive)
        # Don't remove stopwords from queries (they affect meaning)
        original_remove_stopwords = self.remove_stopwords
        self.remove_stopwords = False

        tokens = super().preprocess(text)

        # Restore original setting
        self.remove_stopwords = original_remove_stopwords

        return tokens


__all__ = ['TextPreprocessor', 'QueryPreprocessor']
