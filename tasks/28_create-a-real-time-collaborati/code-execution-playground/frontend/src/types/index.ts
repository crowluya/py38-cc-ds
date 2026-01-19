export interface Language {
  id: string;
  name: string;
  version: string;
}

export interface Session {
  id: string;
  code: string;
  language: string;
  created_at: string;
  updated_at: string;
}

export enum MessageType {
  // Client -> Server
  ExecuteCode = 'execute_code',
  JoinSession = 'join_session',
  LeaveSession = 'leave_session',
  UpdateCode = 'update_code',
  KeepAlive = 'keep_alive',

  // Server -> Client
  ExecutionOutput = 'execution_output',
  ExecutionComplete = 'execution_complete',
  ExecutionError = 'execution_error',
  SessionUpdate = 'session_update',
  UserJoined = 'user_joined',
  UserLeft = 'user_left',
  Error = 'error',
}

export interface WebSocketMessage {
  type: MessageType;
  data: any;
}

export interface ExecuteCodeData {
  session_id: string;
  code: string;
  language: string;
}

export interface ExecutionOutputData {
  session_id: string;
  output: string;
  is_error: boolean;
}

export interface ExecutionCompleteData {
  session_id: string;
  exit_code: number;
  duration_ms: number;
}

export interface JoinSessionData {
  session_id: string;
  user_id?: string;
}
