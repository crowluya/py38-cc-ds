use serde::{Deserialize, Serialize};

/// Complete analysis results for a markdown file
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalysisResults {
    pub file_path: String,
    pub basic_stats: BasicStatistics,
    pub readability: ReadabilityScores,
    pub word_frequency: Vec<WordFrequency>,
    pub sentence_complexity: SentenceComplexity,
    pub writing_style: WritingStyleInsights,
}

/// Basic text statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BasicStatistics {
    pub total_words: usize,
    pub unique_words: usize,
    pub total_sentences: usize,
    pub total_paragraphs: usize,
    pub total_characters: usize,
    pub total_characters_no_spaces: usize,
    pub average_word_length: f64,
    pub vocabulary_richness: f64, // unique_words / total_words
}

/// Readability scores (various indices)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReadabilityScores {
    pub flesch_reading_ease: f64,
    pub flesch_kincaid_grade: f64,
    pub gunning_fog_index: f64,
    pub smog_index: f64,
    pub automated_readability_index: f64,
    pub coleman_liau_index: f64,
}

/// Word frequency entry
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WordFrequency {
    pub word: String,
    pub count: usize,
    pub percentage: f64,
}

/// Sentence complexity metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SentenceComplexity {
    pub average_words_per_sentence: f64,
    pub median_words_per_sentence: f64,
    pub min_sentence_length: usize,
    pub max_sentence_length: usize,
    pub total_syllables: usize,
    pub average_syllables_per_word: f64,
    pub sentence_length_distribution: Vec<SentenceLengthBucket>,
}

/// Sentence length distribution bucket
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SentenceLengthBucket {
    pub range: String,
    pub count: usize,
    pub percentage: f64,
}

/// Writing style insights
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WritingStyleInsights {
    pub passive_voice_percentage: f64,
    pub adverb_count: usize,
    pub adjective_count: usize,
    pub adverb_percentage: f64,
    pub adjective_percentage: f64,
    pub sentence_variety_score: f64,
    pub average_sentence_start_variety: f64,
    pub to_be_verbs_count: usize,
    pub preposition_count: usize,
}

impl Default for AnalysisResults {
    fn default() -> Self {
        Self {
            file_path: String::new(),
            basic_stats: BasicStatistics::default(),
            readability: ReadabilityScores::default(),
            word_frequency: Vec::new(),
            sentence_complexity: SentenceComplexity::default(),
            writing_style: WritingStyleInsights::default(),
        }
    }
}

impl Default for BasicStatistics {
    fn default() -> Self {
        Self {
            total_words: 0,
            unique_words: 0,
            total_sentences: 0,
            total_paragraphs: 0,
            total_characters: 0,
            total_characters_no_spaces: 0,
            average_word_length: 0.0,
            vocabulary_richness: 0.0,
        }
    }
}

impl Default for ReadabilityScores {
    fn default() -> Self {
        Self {
            flesch_reading_ease: 0.0,
            flesch_kincaid_grade: 0.0,
            gunning_fog_index: 0.0,
            smog_index: 0.0,
            automated_readability_index: 0.0,
            coleman_liau_index: 0.0,
        }
    }
}

impl Default for SentenceComplexity {
    fn default() -> Self {
        Self {
            average_words_per_sentence: 0.0,
            median_words_per_sentence: 0.0,
            min_sentence_length: 0,
            max_sentence_length: 0,
            total_syllables: 0,
            average_syllables_per_word: 0.0,
            sentence_length_distribution: Vec::new(),
        }
    }
}

impl Default for WritingStyleInsights {
    fn default() -> Self {
        Self {
            passive_voice_percentage: 0.0,
            adverb_count: 0,
            adjective_count: 0,
            adverb_percentage: 0.0,
            adjective_percentage: 0.0,
            sentence_variety_score: 0.0,
            average_sentence_start_variety: 0.0,
            to_be_verbs_count: 0,
            preposition_count: 0,
        }
    }
}
