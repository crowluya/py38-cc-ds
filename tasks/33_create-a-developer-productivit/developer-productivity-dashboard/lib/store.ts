import { create } from 'zustand';
import { GitMetrics, RepositoryInfo } from './git/types';

interface AnalysisState {
  repository: RepositoryInfo | null;
  metrics: GitMetrics | null;
  isLoading: boolean;
  error: string | null;

  setRepository: (repo: RepositoryInfo) => void;
  setMetrics: (metrics: GitMetrics) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearAnalysis: () => void;
}

export const useAnalysisStore = create<AnalysisState>((set) => ({
  repository: null,
  metrics: null,
  isLoading: false,
  error: null,

  setRepository: (repo) => set({ repository: repo }),
  setMetrics: (metrics) => set({ metrics }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  clearAnalysis: () => set({ repository: null, metrics: null, error: null }),
}));
