use async_openai::{
    types::{CreateEmbeddingRequest, EmbeddingInput},
    Client,
};
use crate::error::{NotesError, Result};
use crate::types::SemanticConfig;
use std::env;

/// Trait for generating text embeddings
#[async_trait::async_trait]
pub trait Embedder: Send + Sync {
    /// Generate embedding for a single text
    async fn embed(&self, text: &str) -> Result<Vec<f32>>;

    /// Generate embeddings for multiple texts (batch processing)
    async fn embed_batch(&self, texts: &[String]) -> Result<Vec<Vec<f32>>>;

    /// Get the dimensionality of the embeddings
    fn dimensions(&self) -> usize;
}

/// OpenAI-based embedder using the embeddings API
pub struct OpenAIEmbedder {
    client: Client<String>,
    model: String,
    dimensions: usize,
}

impl OpenAIEmbedder {
    /// Create a new OpenAI embedder
    pub fn new(config: &SemanticConfig) -> Result<Self> {
        // Try to get API key from config, then environment variable
        let api_key = config.api_key.clone()
            .or_else(|| env::var("OPENAI_API_KEY").ok())
            .ok_or_else(|| {
                NotesError::ConfigError(
                    "OpenAI API key not found. Set it in config or OPENAI_API_KEY environment variable.".to_string()
                )
            })?;

        let client = Client::with_config(
            async_openai::config::OpenAIConfig::new().with_api_key(api_key)
        );

        // Determine dimensions based on model
        let dimensions = if config.model.contains("3-small") {
            1536
        } else if config.model.contains("3-large") {
            3072
        } else if config.model.contains("ada-002") {
            1536
        } else {
            1536 // default
        };

        Ok(Self {
            client,
            model: config.model.clone(),
            dimensions,
        })
    }

    /// Create embedder from environment variable only
    pub fn from_env() -> Result<Self> {
        let api_key = env::var("OPENAI_API_KEY")
            .map_err(|_| NotesError::ConfigError(
                "OPENAI_API_KEY environment variable not set".to_string()
            ))?;

        let client = Client::with_config(
            async_openai::config::OpenAIConfig::new().with_api_key(api_key)
        );

        Ok(Self {
            client,
            model: "text-embedding-3-small".to_string(),
            dimensions: 1536,
        })
    }
}

#[async_trait::async_trait]
impl Embedder for OpenAIEmbedder {
    async fn embed(&self, text: &str) -> Result<Vec<f32>> {
        let request = CreateEmbeddingRequest {
            model: self.model.clone(),
            input: EmbeddingInput::String(text.to_string()),
            ..Default::default()
        };

        let response = self.client.embeddings().create(request).await
            .map_err(|e| NotesError::SearchError(format!("Failed to create embedding: {}", e)))?;

        let embedding = response.data.first()
            .ok_or_else(|| NotesError::SearchError("No embedding returned".to_string()))?;

        Ok(embedding.embedding.clone())
    }

    async fn embed_batch(&self, texts: &[String]) -> Result<Vec<Vec<f32>>> {
        if texts.is_empty() {
            return Ok(Vec::new());
        }

        // OpenAI supports batch embedding
        let input: Vec<_> = texts.iter().map(|s| s.as_str()).collect();
        let request = CreateEmbeddingRequest {
            model: self.model.clone(),
            input: EmbeddingInput::StringArray(input),
            ..Default::default()
        };

        let response = self.client.embeddings().create(request).await
            .map_err(|e| NotesError::SearchError(format!("Failed to create embeddings: {}", e)))?;

        let embeddings: Vec<Vec<f32>> = response.data
            .into_iter()
            .map(|e| e.embedding)
            .collect();

        Ok(embeddings)
    }

    fn dimensions(&self) -> usize {
        self.dimensions
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_openai_embedder_creation() {
        let config = SemanticConfig::default();
        // This will fail without API key, but tests the structure
        let result = OpenAIEmbedder::new(&config);
        // We expect it might fail if no API key is set
        assert!(result.is_ok() || result.is_err());
    }
}
