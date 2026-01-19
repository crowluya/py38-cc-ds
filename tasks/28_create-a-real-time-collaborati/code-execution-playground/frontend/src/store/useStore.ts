import { create } from 'zustand';
import { Session, Language, ExecutionOutputData } from '../types';

interface ExecutionStore {
  // Current session
  currentSession: Session | null;
  setCurrentSession: (session: Session | null) => void;

  // Code and language
  code: string;
  setCode: (code: string) => void;
  language: string;
  setLanguage: (language: string) => void;

  // Execution output
  output: string;
  addOutput: (output: string) => void;
  clearOutput: () => void;
  isExecuting: boolean;
  setIsExecuting: (isExecuting: boolean) => void;

  // Sessions list
  sessions: Session[];
  setSessions: (sessions: Session[]) => void;
  addSession: (session: Session) => void;
  removeSession: (id: string) => void;

  // Supported languages
  languages: Language[];
  setLanguages: (languages: Language[]) => void;

  // Connection status
  isConnected: boolean;
  setIsConnected: (isConnected: boolean) => void;

  // Active users in session
  activeUsers: string[];
  setActiveUsers: (users: string[]) => void;
}

export const useStore = create<ExecutionStore>((set) => ({
  // Current session
  currentSession: null,
  setCurrentSession: (session) => set({ currentSession: session }),

  // Code and language
  code: '',
  setCode: (code) => set({ code }),
  language: 'python',
  setLanguage: (language) => set({ language }),

  // Execution output
  output: '',
  addOutput: (output) => set((state) => ({ output: state.output + output })),
  clearOutput: () => set({ output: '' }),
  isExecuting: false,
  setIsExecuting: (isExecuting) => set({ isExecuting }),

  // Sessions list
  sessions: [],
  setSessions: (sessions) => set({ sessions }),
  addSession: (session) => set((state) => ({ sessions: [...state.sessions, session] })),
  removeSession: (id) => set((state) => ({
    sessions: state.sessions.filter(s => s.id !== id)
  })),

  // Supported languages
  languages: [],
  setLanguages: (languages) => set({ languages }),

  // Connection status
  isConnected: false,
  setIsConnected: (isConnected) => set({ isConnected }),

  // Active users
  activeUsers: [],
  setActiveUsers: (users) => set({ activeUsers: users }),
}));
