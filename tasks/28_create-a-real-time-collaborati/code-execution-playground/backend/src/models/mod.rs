use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Session {
    pub id: String,
    pub code: String,
    pub language: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionResult {
    pub session_id: String,
    pub output: String,
    pub error: Option<String>,
    pub exit_code: Option<i32>,
    pub duration_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WebSocketMessage {
    #[serde(rename = "type")]
    pub msg_type: MessageType,
    pub data: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MessageType {
    // Client -> Server
    ExecuteCode,
    JoinSession,
    LeaveSession,
    UpdateCode,
    KeepAlive,

    // Server -> Client
    ExecutionOutput,
    ExecutionComplete,
    ExecutionError,
    SessionUpdate,
    UserJoined,
    UserLeft,
    Error,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecuteCodeData {
    pub session_id: String,
    pub code: String,
    pub language: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JoinSessionData {
    pub session_id: String,
    pub user_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateCodeData {
    pub session_id: String,
    pub code: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionOutputData {
    pub session_id: String,
    pub output: String,
    pub is_error: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionCompleteData {
    pub session_id: String,
    pub exit_code: i32,
    pub duration_ms: u64,
}
