use anyhow::Result;
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;

mod models;
mod handlers;
mod services;
mod utils;

use handlers::websocket::websocket_handler;
use handlers::rest::create_rest_router;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    let subscriber = FmtSubscriber::builder()
        .with_max_level(Level::INFO)
        .finish();

    tracing::subscriber::set_global_default(subscriber)
        .expect("setting default subscriber failed");

    info!("Starting Code Execution Playground Backend");

    // Initialize database
    services::db::initialize().await?;

    // Build our application with REST and WebSocket routes
    let app = axum::Router::new()
        .fallback(websocket_handler)
        .nest("/api", create_rest_router())
        .layer(
            tower_http::cors::CorsLayer::new()
                .allow_origin(tower_http::cors::Any)
                .allow_methods([axum::http::Method::GET, axum::http::Method::POST, axum::http::Method::DELETE])
                .allow_headers(tower_http::cors::Any)
        )
        .layer(tower_http::trace::TraceLayer::new_for_http());

    // Bind TCP listener
    let listener = tokio::net::TcpListener::bind("0.0.0.0:8080").await?;
    info!("WebSocket server listening on ws://0.0.0.0:8080");

    axum::serve(listener, app).await?;

    Ok(())
}
