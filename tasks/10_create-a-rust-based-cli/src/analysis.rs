use crate::models::*;
use regex::Regex;
use std::collections::{HashMap, HashSet};

/// Analyzes text and returns comprehensive statistics
pub struct TextAnalyzer {
    text: String,
    words: Vec<String>,
    sentences: Vec<String>,
}

impl TextAnalyzer {
    /// Creates a new TextAnalyzer from the given text
    pub fn new(text: &str) -> Self {
        let cleaned_text = text.trim().to_string();
        let words = Self::tokenize_words(&cleaned_text);
        let sentences = Self::tokenize_sentences(&cleaned_text);

        Self {
            text: cleaned_text,
            words,
            sentences,
        }
    }

    /// Tokenizes text into words
    fn tokenize_words(text: &str) -> Vec<String> {
        let re = Regex::new(r"[a-zA-Z0-9']+").unwrap();
        re.find_iter(text)
            .map(|m| m.as_str().to_lowercase())
            .collect()
    }

    /// Tokenizes text into sentences
    fn tokenize_sentences(text: &str) -> Vec<String> {
        // Simple sentence splitting - can be improved
        let re = Regex::new(r"[.!?]+\s+").unwrap();
        let sentences: Vec<String> = re
            .split(text)
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .collect();

        sentences
    }

    /// Counts syllables in a word using heuristic approach
    fn count_syllables(word: &str) -> usize {
        let word_lower = word.to_lowercase();
        let word_lower = word_lower.trim();

        if word_lower.is_empty() {
            return 0;
        }

        // Remove trailing 'e' unless it's the only vowel
        let mut processed = if word_lower.ends_with('e') && word_lower.len() > 1 {
            word_lower[..word_lower.len() - 1].to_string()
        } else {
            word_lower.to_string()
        };

        // Count vowel groups
        let vowel_re = Regex::new(r"[aeiouy]+").unwrap();
        let syllable_count = vowel_re.find_iter(&processed).count();

        syllable_count.max(1)
    }

    /// Calculates basic statistics
    pub fn calculate_basic_stats(&self) -> BasicStatistics {
        let total_words = self.words.len();
        let unique_words: HashSet<&String> = self.words.iter().collect();
        let total_sentences = self.sentences.len();
        let total_paragraphs = self.text.split("\n\n").filter(|p| !p.trim().is_empty()).count();
        let total_characters = self.text.chars().count();
        let total_characters_no_spaces = self.text.chars().filter(|c| !c.is_whitespace()).count();

        let average_word_length = if total_words > 0 {
            self.words.iter().map(|w| w.len()).sum::<usize>() as f64 / total_words as f64
        } else {
            0.0
        };

        let vocabulary_richness = if total_words > 0 {
            unique_words.len() as f64 / total_words as f64
        } else {
            0.0
        };

        BasicStatistics {
            total_words,
            unique_words: unique_words.len(),
            total_sentences,
            total_paragraphs,
            total_characters,
            total_characters_no_spaces,
            average_word_length,
            vocabulary_richness,
        }
    }

    /// Calculates readability scores
    pub fn calculate_readability_scores(&self) -> ReadabilityScores {
        let stats = self.calculate_basic_stats();
        let total_sentences = stats.total_sentences as f64;
        let total_words = stats.total_words as f64;

        let total_syllables: usize = self.words.iter().map(|w| Self::count_syllables(w)).sum();
        let total_syllables = total_syllables as f64;

        let flesch_reading_ease = if total_sentences > 0.0 && total_words > 0.0 {
            206.835 - (1.015 * (total_words / total_sentences)) - (84.6 * (total_syllables / total_words))
        } else {
            0.0
        };

        let flesch_kincaid_grade = if total_sentences > 0.0 && total_words > 0.0 {
            (0.39 * (total_words / total_sentences)) + (11.8 * (total_syllables / total_words)) - 15.59
        } else {
            0.0
        };

        let gunning_fog_index = if total_sentences > 0.0 && total_words > 0.0 {
            let complex_words = self.count_complex_words();
            0.4 * ((total_words / total_sentences) + (100.0 * (complex_words as f64 / total_words)))
        } else {
            0.0
        };

        let smog_index = if total_sentences > 0.0 {
            let polysyllables = self.count_polysyllables() as f64;
            1.0430 * (polysyllables * (30.0 / total_sentences)).sqrt() + 3.1291
        } else {
            0.0
        };

        let automated_readability_index = if total_sentences > 0.0 && total_words > 0.0 {
            let total_characters = stats.total_characters as f64;
            4.71 * (total_characters / total_words) + 0.5 * (total_words / total_sentences) - 21.43
        } else {
            0.0
        };

        let coleman_liau_index = if total_words > 0.0 {
            let avg_letters_per_100_words = (stats.total_characters_no_spaces as f64 / total_words) * 100.0;
            let avg_sentences_per_100_words = (total_sentences / total_words) * 100.0;
            0.0588 * avg_letters_per_100_words - 0.296 * avg_sentences_per_100_words - 15.8
        } else {
            0.0
        };

        ReadabilityScores {
            flesch_reading_ease,
            flesch_kincaid_grade,
            gunning_fog_index,
            smog_index,
            automated_readability_index,
            coleman_liau_index,
        }
    }

    /// Counts complex words (3+ syllables, excluding suffixes)
    fn count_complex_words(&self) -> usize {
        self.words
            .iter()
            .filter(|w| Self::count_syllables(w) >= 3)
            .count()
    }

    /// Counts polysyllabic words (4+ syllables)
    fn count_polysyllables(&self) -> usize {
        self.words
            .iter()
            .filter(|w| Self::count_syllables(w) >= 4)
            .count()
    }

    /// Calculates word frequency
    pub fn calculate_word_frequency(&self, top_n: usize, min_length: usize) -> Vec<WordFrequency> {
        let mut word_counts: HashMap<String, usize> = HashMap::new();

        for word in &self.words {
            if word.len() >= min_length {
                *word_counts.entry(word.clone()).or_insert(0) += 1;
            }
        }

        let mut word_freq: Vec<WordFrequency> = word_counts
            .into_iter()
            .map(|(word, count)| {
                let percentage = (count as f64 / self.words.len() as f64) * 100.0;
                WordFrequency { word, count, percentage }
            })
            .collect();

        word_freq.sort_by(|a, b| b.count.cmp(&a.count));

        word_freq.truncate(top_n);
        word_freq
    }

    /// Calculates sentence complexity metrics
    pub fn calculate_sentence_complexity(&self) -> SentenceComplexity {
        let sentence_lengths: Vec<usize> = self
            .sentences
            .iter()
            .map(|s| Self::tokenize_words(s).len())
            .filter(|&len| len > 0)
            .collect();

        if sentence_lengths.is_empty() {
            return SentenceComplexity::default();
        }

        let total_syllables: usize = self.words.iter().map(|w| Self::count_syllables(w)).sum();
        let average_words_per_sentence = sentence_lengths.iter().sum::<usize>() as f64 / sentence_lengths.len() as f64;

        let mut sorted_lengths = sentence_lengths.clone();
        sorted_lengths.sort();
        let median_words_per_sentence = if sorted_lengths.len() % 2 == 0 {
            let mid = sorted_lengths.len() / 2;
            (sorted_lengths[mid - 1] + sorted_lengths[mid]) as f64 / 2.0
        } else {
            sorted_lengths[sorted_lengths.len() / 2] as f64
        };

        let min_sentence_length = *sentence_lengths.iter().min().unwrap_or(&0);
        let max_sentence_length = *sentence_lengths.iter().max().unwrap_or(&0);
        let average_syllables_per_word = if !self.words.is_empty() {
            total_syllables as f64 / self.words.len() as f64
        } else {
            0.0
        };

        let sentence_length_distribution = Self::create_sentence_distribution(&sentence_lengths);

        SentenceComplexity {
            average_words_per_sentence,
            median_words_per_sentence,
            min_sentence_length,
            max_sentence_length,
            total_syllables,
            average_syllables_per_word,
            sentence_length_distribution,
        }
    }

    /// Creates sentence length distribution buckets
    fn create_sentence_distribution(lengths: &[usize]) -> Vec<SentenceLengthBucket> {
        let ranges = vec![
            ("1-10", 1..=10),
            ("11-20", 11..=20),
            ("21-30", 21..=30),
            ("31-40", 31..=40),
            ("41-50", 41..=50),
            ("50+", 51..=usize::MAX),
        ];

        let total = lengths.len() as f64;

        ranges
            .into_iter()
            .map(|(name, range)| {
                let count = lengths.iter().filter(|&&l| range.contains(&l)).count();
                let percentage = (count as f64 / total) * 100.0;
                SentenceLengthBucket {
                    range: name.to_string(),
                    count,
                    percentage,
                }
            })
            .collect()
    }

    /// Analyzes writing style
    pub fn analyze_writing_style(&self) -> WritingStyleInsights {
        let passive_voice_count = self.detect_passive_voice();
        let total_sentences = self.sentences.len() as f64;

        let passive_voice_percentage = if total_sentences > 0.0 {
            (passive_voice_count as f64 / total_sentences) * 100.0
        } else {
            0.0
        };

        let adverb_count = self.count_adverbs();
        let adjective_count = self.count_adjectives();
        let total_words = self.words.len() as f64;

        let adverb_percentage = if total_words > 0.0 {
            (adverb_count as f64 / total_words) * 100.0
        } else {
            0.0
        };

        let adjective_percentage = if total_words > 0.0 {
            (adjective_count as f64 / total_words) * 100.0
        } else {
            0.0
        };

        let to_be_verbs_count = self.count_to_be_verbs();
        let preposition_count = self.count_prepositions();

        let sentence_variety_score = self.calculate_sentence_variety();
        let average_sentence_start_variety = self.calculate_sentence_start_variety();

        WritingStyleInsights {
            passive_voice_percentage,
            adverb_count,
            adjective_count,
            adverb_percentage,
            adjective_percentage,
            sentence_variety_score,
            average_sentence_start_variety,
            to_be_verbs_count,
            preposition_count,
        }
    }

    /// Detects passive voice (heuristic-based)
    fn detect_passive_voice(&self) -> usize {
        let passive_re = Regex::new(r"\b(was|were|been|being)\s+\w+ed\b").unwrap();
        self.sentences
            .iter()
            .filter(|s| passive_re.is_match(s))
            .count()
    }

    /// Counts adverbs (words ending in -ly)
    fn count_adverbs(&self) -> usize {
        self.words
            .iter()
            .filter(|w| w.ends_with("ly") && w.len() > 3)
            .count()
    }

    /// Counts adjectives (heuristic-based)
    fn count_adjectives(&self) -> usize {
        let adjective_re = Regex::new(r"\b\w+(ous|able|ible|al|ful|ic|ive|less|ent)\b").unwrap();
        self.words.iter().filter(|w| adjective_re.is_match(w)).count()
    }

    /// Counts "to be" verbs
    fn count_to_be_verbs(&self) -> usize {
        let to_be = ["am", "is", "are", "was", "were", "be", "been", "being"];
        self.words
            .iter()
            .filter(|w| to_be.contains(&w.as_str()))
            .count()
    }

    /// Counts common prepositions
    fn count_prepositions(&self) -> usize {
        let prepositions = [
            "about", "above", "across", "after", "against", "along", "among", "around", "at",
            "before", "behind", "below", "beneath", "beside", "between", "beyond", "by", "down",
            "during", "except", "for", "from", "in", "inside", "into", "like", "near", "of",
            "off", "on", "onto", "out", "over", "past", "since", "through", "throughout", "to",
            "toward", "under", "underneath", "until", "up", "upon", "with", "within", "without",
        ];
        self.words
            .iter()
            .filter(|w| prepositions.contains(&w.as_str()))
            .count()
    }

    /// Calculates sentence variety score
    fn calculate_sentence_variety(&self) -> f64 {
        if self.sentences.is_empty() {
            return 0.0;
        }

        let lengths: Vec<usize> = self
            .sentences
            .iter()
            .map(|s| Self::tokenize_words(s).len())
            .collect();

        let unique_lengths: HashSet<usize> = lengths.into_iter().collect();

        (unique_lengths.len() as f64 / self.sentences.len() as f64) * 100.0
    }

    /// Calculates sentence start variety
    fn calculate_sentence_start_variety(&self) -> f64 {
        if self.sentences.is_empty() {
            return 0.0;
        }

        let starts: Vec<String> = self
            .sentences
            .iter()
            .filter_map(|s| Self::tokenize_words(s).first().cloned())
            .collect();

        let unique_starts: HashSet<&String> = starts.iter().collect();

        (unique_starts.len() as f64 / starts.len() as f64) * 100.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_count_syllables() {
        assert_eq!(TextAnalyzer::count_syllables("hello"), 2);
        assert_eq!(TextAnalyzer::count_syllables("world"), 1);
        assert_eq!(TextAnalyzer::count_syllables("beautiful"), 3);
    }

    #[test]
    fn test_basic_stats() {
        let analyzer = TextAnalyzer::new("This is a test. This is only a test.");
        let stats = analyzer.calculate_basic_stats();
        assert_eq!(stats.total_words, 9);
        assert_eq!(stats.total_sentences, 2);
    }

    #[test]
    fn test_word_frequency() {
        let analyzer = TextAnalyzer::new("test test test example example word");
        let freq = analyzer.calculate_word_frequency(10, 1);
        assert_eq!(freq[0].word, "test");
        assert_eq!(freq[0].count, 3);
        assert_eq!(freq[1].word, "example");
        assert_eq!(freq[1].count, 2);
    }
}
