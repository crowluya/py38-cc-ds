use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::{Mutex, mpsc::unbounded_channel, UnboundedSender};
use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        State,
    },
    response::IntoResponse,
};
use futures_util::{SinkExt, StreamExt};
use serde_json::json;
use tracing::{info, error, debug};
use uuid::Uuid;

use crate::models::*;
use crate::services::DockerExecutor;

type SessionUsers = Arc<Mutex<HashMap<String, Vec<String>>>>;

#[derive(Clone)]
pub struct AppState {
    pub executor: Arc<DockerExecutor>,
    pub session_users: SessionUsers,
}

pub async fn websocket_handler(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_socket(socket, state))
}

async fn handle_socket(socket: WebSocket, state: AppState) {
    let (mut sender, mut receiver) = socket.split();
    let user_id = Uuid::new_v4().to_string();

    info!("New WebSocket connection: {}", user_id);

    while let Some(msg) = receiver.next().await {
        match msg {
            Ok(Message::Text(text)) => {
                debug!("Received message: {}", text);

                if let Ok(ws_msg) = serde_json::from_str::<WebSocketMessage>(&text) {
                    match ws_msg.msg_type {
                        MessageType::ExecuteCode => {
                            if let Ok(data) = serde_json::from_value::<ExecuteCodeData>(ws_msg.data) {
                                tokio::spawn(handle_execution(
                                    data,
                                    user_id.clone(),
                                    sender.clone(),
                                    state.clone(),
                                ));
                            }
                        }
                        MessageType::JoinSession => {
                            if let Ok(data) = serde_json::from_value::<JoinSessionData>(ws_msg.data) {
                                handle_join_session(data, user_id.clone(), &state).await;
                            }
                        }
                        MessageType::LeaveSession => {
                            if let Ok(data) = serde_json::from_value::<JoinSessionData>(ws_msg.data) {
                                handle_leave_session(data, user_id.clone(), &state).await;
                            }
                        }
                        MessageType::KeepAlive => {
                            // Respond to keep-alive
                            let response = WebSocketMessage {
                                msg_type: MessageType::KeepAlive,
                                data: json!({ "status": "alive" }),
                            };
                            let _ = sender.send(Message::Text(serde_json::to_string(&response).unwrap())).await;
                        }
                        _ => {
                            debug!("Unhandled message type: {:?}", ws_msg.msg_type);
                        }
                    }
                }
            }
            Ok(Message::Close(_)) => {
                info!("Client {} disconnected", user_id);
                break;
            }
            Err(e) => {
                error!("WebSocket error: {:?}", e);
                break;
            }
            _ => {}
        }
    }
}

async fn handle_execution(
    data: ExecuteCodeData,
    user_id: String,
    mut sender: futures_util::stream::SplitSink<WebSocket, Message>,
    state: AppState,
) {
    let (output_tx, mut output_rx) = unbounded_channel::<String>();
    let session_id = data.session_id.clone();

    info!("Executing code for session: {} by user: {}", session_id, user_id);

    // Spawn task to forward output to WebSocket
    let sender_clone = sender.clone();
    let session_id_clone = session_id.clone();
    tokio::spawn(async move {
        while let Some(output) = output_rx.recv().await {
            let response = WebSocketMessage {
                msg_type: MessageType::ExecutionOutput,
                data: serde_json::to_value(ExecutionOutputData {
                    session_id: session_id_clone.clone(),
                    output,
                    is_error: false,
                }).unwrap(),
            };

            if let Ok(text) = serde_json::to_string(&response) {
                let _ = sender_clone.send(Message::Text(text)).await;
            }
        }
    });

    // Execute code
    let start_time = std::time::Instant::now();
    let result = state.executor.execute_code(
        &data.code,
        &data.language,
        &session_id,
        output_tx,
    ).await;

    let duration = start_time.elapsed();
    let exit_code = result.unwrap_or(-1);

    // Send completion message
    let complete_msg = WebSocketMessage {
        msg_type: MessageType::ExecutionComplete,
        data: serde_json::to_value(ExecutionCompleteData {
            session_id,
            exit_code,
            duration_ms: duration.as_millis() as u64,
        }).unwrap(),
    };

    if let Ok(text) = serde_json::to_string(&complete_msg) {
        let _ = sender.send(Message::Text(text)).await;
    }
}

async fn handle_join_session(
    data: JoinSessionData,
    user_id: String,
    state: &AppState,
) {
    let mut users = state.session_users.lock().await;
    users.entry(data.session_id.clone())
        .or_insert_with(Vec::new)
        .push(user_id.clone());

    info!("User {} joined session {}", user_id, data.session_id);
}

async fn handle_leave_session(
    data: JoinSessionData,
    user_id: String,
    state: &AppState,
) {
    let mut users = state.session_users.lock().await;
    if let Some(session_users) = users.get_mut(&data.session_id) {
        session_users.retain(|u| u != &user_id);
    }

    info!("User {} left session {}", user_id, data.session_id);
}
