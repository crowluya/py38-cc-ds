import axios from 'axios';
import { Session, Language } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api';

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const sessionService = {
  async createSession(code: string, language: string): Promise<Session> {
    const response = await api.post('/sessions', { code, language });
    return response.data;
  },

  async getSession(id: string): Promise<Session> {
    const response = await api.get(`/sessions/${id}`);
    return response.data;
  },

  async listSessions(): Promise<Session[]> {
    const response = await api.get('/sessions');
    return response.data;
  },

  async deleteSession(id: string): Promise<void> {
    await api.delete(`/sessions/${id}`);
  },
};

export const languageService = {
  async getLanguages(): Promise<Language[]> {
    const response = await api.get('/languages');
    return response.data;
  },
};
