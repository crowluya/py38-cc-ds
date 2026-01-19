mod analysis;
mod cli;
mod error;
mod io;
mod models;
mod output;
mod parser;

use crate::analysis::TextAnalyzer;
use crate::cli::Args;
use crate::error::{AnalysisError, Result};
use crate::io::{read_markdown_file, write_to_file};
use crate::output::OutputFormatter;
use crate::parser::{clean_text, extract_text_from_markdown};
use clap::Parser;
use std::path::Path;

fn main() {
    if let Err(e) = run() {
        eprintln!("{} {}",
            "Error:".red().bold(),
            e
        );
        std::process::exit(1);
    }
}

fn run() -> Result<()> {
    let args = Args::parse();

    // Read the markdown file
    let markdown_content = read_markdown_file(Path::new(&args.file_path))?;

    // Extract plain text from markdown
    let plain_text = extract_text_from_markdown(&markdown_content, args.include_code_blocks)?;
    let cleaned_text = clean_text(&plain_text);

    if cleaned_text.is_empty() {
        return Err(AnalysisError::AnalysisError(
            "No extractable text found in the markdown file".to_string(),
        ));
    }

    // Perform analysis
    let analyzer = TextAnalyzer::new(&cleaned_text);
    let basic_stats = analyzer.calculate_basic_stats();
    let readability_scores = analyzer.calculate_readability_scores();
    let word_frequency = analyzer.calculate_word_frequency(args.top_words, args.min_word_length);
    let sentence_complexity = analyzer.calculate_sentence_complexity();
    let writing_style = analyzer.analyze_writing_style();

    let results = crate::models::AnalysisResults {
        file_path: args.file_path.to_string_lossy().to_string(),
        basic_stats,
        readability: readability_scores,
        word_frequency,
        sentence_complexity,
        writing_style,
    };

    // Output results based on format
    match args.output {
        cli::OutputFormat::Console => {
            let formatted = OutputFormatter::format_console(&results, args.verbose);
            if let Some(output_path) = args.output_file {
                write_to_file(Path::new(&output_path), &formatted)?;
                println!("\n{} Results written to {}",
                    "✓".green(),
                    output_path.to_string_lossy().cyan()
                );
            } else {
                println!("{}", formatted);
            }
        }
        cli::OutputFormat::Json => {
            let json = OutputFormatter::export_json(&results)?;
            if let Some(output_path) = args.output_file {
                write_to_file(Path::new(&output_path), &json)?;
                println!("{} JSON results written to {}",
                    "✓".green(),
                    output_path.to_string_lossy().cyan()
                );
            } else {
                println!("{}", json);
            }
        }
        cli::OutputFormat::Csv => {
            let csv = OutputFormatter::export_csv(&results)?;
            if let Some(output_path) = args.output_file {
                write_to_file(Path::new(&output_path), &csv)?;
                println!("{} CSV results written to {}",
                    "✓".green(),
                    output_path.to_string_lossy().cyan()
                );
            } else {
                println!("{}", csv);
            }
        }
    }

    Ok(())
}
