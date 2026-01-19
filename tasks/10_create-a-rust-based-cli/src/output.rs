use colored::*;
use crate::models::*;
use crate::error::Result;
use std::io::Write;

/// Formats and outputs analysis results
pub struct OutputFormatter;

impl OutputFormatter {
    /// Formats results for console output
    pub fn format_console(results: &AnalysisResults, verbose: bool) -> String {
        let mut output = String::new();

        // Header
        output.push_str(&format!(
            "\n{} {}\n",
            "📊 Text Analysis Report".bold().cyan(),
            format!("for {}", results.file_path).dimmed()
        ));
        output.push_str(&"═".repeat(80));
        output.push_str("\n\n");

        // Basic Statistics
        output.push_str(&format!("{}\n", "Basic Statistics".bold().white()));
        output.push_str(&"─".repeat(40));
        output.push_str("\n");
        Self::print_basic_stats(&mut output, &results.basic_stats);
        output.push_str("\n");

        // Readability Scores
        output.push_str(&format!("{}\n", "Readability Scores".bold().white()));
        output.push_str(&"─".repeat(40));
        output.push_str("\n");
        Self::print_readability_scores(&mut output, &results.readability);
        output.push_str("\n");

        // Sentence Complexity
        output.push_str(&format!("{}\n", "Sentence Complexity".bold().white()));
        output.push_str(&"─".repeat(40));
        output.push_str("\n");
        Self::print_sentence_complexity(&mut output, &results.sentence_complexity);
        output.push_str("\n");

        // Writing Style
        output.push_str(&format!("{}\n", "Writing Style Insights".bold().white()));
        output.push_str(&"─".repeat(40));
        output.push_str("\n");
        Self::print_writing_style(&mut output, &results.writing_style);
        output.push_str("\n");

        // Word Frequency
        output.push_str(&format!("{}\n", "Top Word Frequency".bold().white()));
        output.push_str(&"─".repeat(40));
        output.push_str("\n");
        Self::print_word_frequency(&mut output, &results.word_frequency);
        output.push_str("\n");

        if verbose {
            // Sentence Length Distribution
            output.push_str(&format!("{}\n", "Sentence Length Distribution".bold().white()));
            output.push_str(&"─".repeat(40));
            output.push_str("\n");
            Self::print_sentence_distribution(&mut output, &results.sentence_complexity.sentence_length_distribution);
            output.push_str("\n");
        }

        output.push_str(&"═".repeat(80));
        output.push_str("\n");

        output
    }

    fn print_basic_stats(output: &mut String, stats: &BasicStatistics) {
        writeln!(output, "  Total Words:              {}", stats.total_words.to_string().green()).unwrap();
        writeln!(output, "  Unique Words:             {}", stats.unique_words.to_string().green()).unwrap();
        writeln!(output, "  Total Sentences:          {}", stats.total_sentences.to_string().green()).unwrap();
        writeln!(output, "  Total Paragraphs:         {}", stats.total_paragraphs.to_string().green()).unwrap();
        writeln!(output, "  Total Characters:         {}", stats.total_characters.to_string().green()).unwrap();
        writeln!(output, "  Characters (no spaces):   {}", stats.total_characters_no_spaces.to_string().green()).unwrap();
        writeln!(output, "  Avg Word Length:          {:.2}", stats.average_word_length).unwrap();
        writeln!(output, "  Vocabulary Richness:      {:.2}%", stats.vocabulary_richness * 100.0).unwrap();
    }

    fn print_readability_scores(output: &mut String, scores: &ReadabilityScores) {
        writeln!(output, "  Flesch Reading Ease:      {:.2} {}", scores.flesch_reading_ease,
            Self::get_reading_level_description(scores.flesch_reading_ease).dimmed()).unwrap();
        writeln!(output, "  Flesch-Kincaid Grade:     {:.2}", scores.flesch_kincaid_grade).unwrap();
        writeln!(output, "  Gunning Fog Index:        {:.2}", scores.gunning_fog_index).unwrap();
        writeln!(output, "  SMOG Index:               {:.2}", scores.smog_index).unwrap();
        writeln!(output, "  ARI:                      {:.2}", scores.automated_readability_index).unwrap();
        writeln!(output, "  Coleman-Liau Index:       {:.2}", scores.coleman_liau_index).unwrap();
    }

    fn get_reading_level_description(score: f64) -> String {
        match score {
            s if s >= 90.0 => "(5th grade - Very Easy)".to_string(),
            s if s >= 80.0 => "(6th grade - Easy)".to_string(),
            s if s >= 70.0 => "(7th grade - Fairly Easy)".to_string(),
            s if s >= 60.0 => "(8th-9th grade - Standard)".to_string(),
            s if s >= 50.0 => "(10th-12th grade - Fairly Difficult)".to_string(),
            s if s >= 30.0 => "(College - Difficult)".to_string(),
            _ => "(Professional - Very Difficult)".to_string(),
        }
    }

    fn print_sentence_complexity(output: &mut String, complexity: &SentenceComplexity) {
        writeln!(output, "  Avg Words/Sentence:       {:.2}", complexity.average_words_per_sentence).unwrap();
        writeln!(output, "  Median Words/Sentence:    {:.2}", complexity.median_words_per_sentence).unwrap();
        writeln!(output, "  Min Sentence Length:      {}", complexity.min_sentence_length).unwrap();
        writeln!(output, "  Max Sentence Length:      {}", complexity.max_sentence_length).unwrap();
        writeln!(output, "  Total Syllables:          {}", complexity.total_syllables).unwrap();
        writeln!(output, "  Avg Syllables/Word:       {:.2}", complexity.average_syllables_per_word).unwrap();
    }

    fn print_writing_style(output: &mut String, style: &WritingStyleInsights) {
        writeln!(output, "  Passive Voice:            {:.1}%", style.passive_voice_percentage,
            if style.passive_voice_percentage < 10.0 { " ✓".green() } else { " ⚠".yellow() }).unwrap();
        writeln!(output, "  Adverb Count:             {} ({:.1}%)", style.adverb_count, style.adverb_percentage).unwrap();
        writeln!(output, "  Adjective Count:          {} ({:.1}%)", style.adjective_count, style.adjective_percentage).unwrap();
        writeln!(output, "  To-Be Verbs Count:        {}", style.to_be_verbs_count).unwrap();
        writeln!(output, "  Preposition Count:        {}", style.preposition_count).unwrap();
        writeln!(output, "  Sentence Variety Score:   {:.1}%", style.sentence_variety_score).unwrap();
        writeln!(output, "  Sentence Start Variety:   {:.1}%", style.average_sentence_start_variety).unwrap();
    }

    fn print_word_frequency(output: &mut String, freq: &[WordFrequency]) {
        if freq.is_empty() {
            writeln!(output, "  {}", "No words found".italic()).unwrap();
            return;
        }

        let max_word_len = freq.iter().map(|w| w.word.len()).max().unwrap_or(10);
        let header1 = "Word";
        let header2 = "Count";
        let header3 = "Percentage";

        writeln!(output, "  {:<width$}  {:>6}  {:>10}", header1.cyan(), header2.cyan(), header3.cyan(),
            width = max_word_len).unwrap();
        writeln!(output, "  {}", "─".repeat(max_word_len + 21)).unwrap();

        for (i, word_freq) in freq.iter().enumerate() {
            let rank = format!("{}.", i + 1).dimmed().to_string();
            writeln!(output, "  {} {:<width$}  {:>6}  {:>9.1}%",
                rank, word_freq.word.green(), word_freq.count, word_freq.percentage,
                width = max_word_len - 2).unwrap();
        }
    }

    fn print_sentence_distribution(output: &mut String, distribution: &[SentenceLengthBucket]) {
        for bucket in distribution {
            writeln!(output,
                "  {:<10}  {:>6} sentences  ({:>5.1}%)  {}",
                bucket.range.cyan(),
                bucket.count,
                bucket.percentage,
                "█".repeat((bucket.percentage / 2.0) as usize).blue()
            ).unwrap();
        }
    }

    /// Exports results to JSON format
    pub fn export_json(results: &AnalysisResults) -> Result<String> {
        let json = serde_json::to_string_pretty(results)?;
        Ok(json)
    }

    /// Exports results to CSV format
    pub fn export_csv(results: &AnalysisResults) -> Result<String> {
        let mut csv_output = String::new();

        // Basic Statistics
        writeln!(csv_output, "Metric,Value").unwrap();
        writeln!(csv_output, "File Path,\"{}\"", results.file_path).unwrap();
        writeln!(csv_output, "Total Words,{}", results.basic_stats.total_words).unwrap();
        writeln!(csv_output, "Unique Words,{}", results.basic_stats.unique_words).unwrap();
        writeln!(csv_output, "Total Sentences,{}", results.basic_stats.total_sentences).unwrap();
        writeln!(csv_output, "Total Paragraphs,{}", results.basic_stats.total_paragraphs).unwrap();
        writeln!(csv_output, "Total Characters,{}", results.basic_stats.total_characters).unwrap();
        writeln!(csv_output, "Average Word Length,{:.2}", results.basic_stats.average_word_length).unwrap();
        writeln!(csv_output, "Vocabulary Richness,{:.4}", results.basic_stats.vocabulary_richness).unwrap();

        // Readability Scores
        writeln!(csv_output, "\nReadability Metric,Score").unwrap();
        writeln!(csv_output, "Flesch Reading Ease,{:.2}", results.readability.flesch_reading_ease).unwrap();
        writeln!(csv_output, "Flesch-Kincaid Grade,{:.2}", results.readability.flesch_kincaid_grade).unwrap();
        writeln!(csv_output, "Gunning Fog Index,{:.2}", results.readability.gunning_fog_index).unwrap();
        writeln!(csv_output, "SMOG Index,{:.2}", results.readability.smog_index).unwrap();
        writeln!(csv_output, "Automated Readability Index,{:.2}", results.readability.automated_readability_index).unwrap();
        writeln!(csv_output, "Coleman-Liau Index,{:.2}", results.readability.coleman_liau_index).unwrap();

        // Sentence Complexity
        writeln!(csv_output, "\nComplexity Metric,Value").unwrap();
        writeln!(csv_output, "Average Words Per Sentence,{:.2}", results.sentence_complexity.average_words_per_sentence).unwrap();
        writeln!(csv_output, "Median Words Per Sentence,{:.2}", results.sentence_complexity.median_words_per_sentence).unwrap();
        writeln!(csv_output, "Min Sentence Length,{}", results.sentence_complexity.min_sentence_length).unwrap();
        writeln!(csv_output, "Max Sentence Length,{}", results.sentence_complexity.max_sentence_length).unwrap();
        writeln!(csv_output, "Total Syllables,{}", results.sentence_complexity.total_syllables).unwrap();
        writeln!(csv_output, "Average Syllables Per Word,{:.2}", results.sentence_complexity.average_syllables_per_word).unwrap();

        // Writing Style
        writeln!(csv_output, "\nStyle Metric,Value").unwrap();
        writeln!(csv_output, "Passive Voice Percentage,{:.2}", results.writing_style.passive_voice_percentage).unwrap();
        writeln!(csv_output, "Adverb Count,{}", results.writing_style.adverb_count).unwrap();
        writeln!(csv_output, "Adjective Count,{}", results.writing_style.adjective_count).unwrap();
        writeln!(csv_output, "Adverb Percentage,{:.2}", results.writing_style.adverb_percentage).unwrap();
        writeln!(csv_output, "Adjective Percentage,{:.2}", results.writing_style.adjective_percentage).unwrap();
        writeln!(csv_output, "To-Be Verbs Count,{}", results.writing_style.to_be_verbs_count).unwrap();
        writeln!(csv_output, "Preposition Count,{}", results.writing_style.preposition_count).unwrap();

        // Word Frequency
        writeln!(csv_output, "\nWord,Count,Percentage").unwrap();
        for word_freq in &results.word_frequency {
            writeln!(csv_output, "{},{},{:.2}", word_freq.word, word_freq.count, word_freq.percentage).unwrap();
        }

        Ok(csv_output)
    }
}
