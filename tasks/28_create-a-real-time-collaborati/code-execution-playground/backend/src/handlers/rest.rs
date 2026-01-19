use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
    Router,
};
use serde_json::json;
use uuid::Uuid;
use chrono::Utc;

use crate::models::Session;
use crate::services::Database;

pub fn create_rest_router() -> Router {
    // Note: For simplicity, we're using in-memory database
    // In production, you'd inject the database state
    Router::new()
        .axum_route(
            "/sessions",
            axum::routing::post(create_session).get(list_sessions),
        )
        .axum_route("/sessions/:id", axum::routing::get(get_session).delete(delete_session))
        .axum_route("/languages", axum::routing::get(list_languages))
}

async fn create_session(
    Json(payload): Json<serde_json::Value>,
) -> impl IntoResponse {
    let code = payload.get("code")
        .and_then(|v| v.as_str())
        .unwrap_or("");
    let language = payload.get("language")
        .and_then(|v| v.as_str())
        .unwrap_or("python");

    let session = Session {
        id: Uuid::new_v4().to_string(),
        code: code.to_string(),
        language: language.to_string(),
        created_at: Utc::now(),
        updated_at: Utc::now(),
    };

    // In production, save to database here
    // db.create_session(&session).await?;

    (StatusCode::CREATED, Json(session))
}

async fn list_sessions() -> impl IntoResponse {
    // In production, fetch from database
    let sessions: Vec<Session> = vec![];
    Json(sessions)
}

async fn get_session(Path(id): Path<String>) -> impl IntoResponse {
    // In production, fetch from database
    (StatusCode::OK, Json(json!({ "id": id, "code": "", "language": "python" })))
}

async fn delete_session(Path(id): Path<String>) -> impl IntoResponse {
    // In production, delete from database
    (StatusCode::NO_CONTENT, Json(json!({ "message": "Session deleted" })))
}

async fn list_languages() -> impl IntoResponse {
    let languages = vec![
        json!({ "id": "python", "name": "Python 3", "version": "3.11" }),
        json!({ "id": "javascript", "name": "JavaScript (Node.js)", "version": "20" }),
        json!({ "id": "rust", "name": "Rust", "version": "1.75" }),
        json!({ "id": "go", "name": "Go", "version": "1.21" }),
    ];

    Json(languages)
}
