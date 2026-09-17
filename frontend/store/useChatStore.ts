/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable @typescript-eslint/no-explicit-any */
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface Turn {
  id: string;
  query: string;
  status: 'streaming' | 'completed' | 'interrupted' | 'terminated' | 'error';
  progressSteps: string[];
  response?: string;
  knowledgeSource?: string;
  requiresExternalResearch?: boolean;
  degraded?: boolean;
  terminationReason?: string;
  interrupt?: any;
  error?: string;
}

export interface Session {
  id: string; // thread_id
  title: string;
  createdAt: string;
  updatedAt: string;
}

interface ChatStore {
  sessions: Session[];
  activeSessionId: string | null;
  turnsBySession: Record<string, Turn[]>;
  pendingQuery: string | null;

  setActiveSession: (id: string | null) => void;
  createSession: (id: string, initialQuery: string) => Session;
  rekeySession: (tempId: string, realId: string) => void;
  renameSession: (id: string, newTitle: string) => void;
  deleteSession: (id: string) => void;

  appendTurn: (sessionId: string, turn: Turn) => void;
  updateTurn: (sessionId: string, turnId: string, patch: Partial<Turn>) => void;

  setPendingQuery: (query: string | null) => void;
  clearPendingQuery: () => void;
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      sessions: [],
      activeSessionId: null,
      turnsBySession: {},
      pendingQuery: null,

      setActiveSession: (id) => set({ activeSessionId: id }),

      createSession: (id, initialQuery) => {
        const truncatedTitle =
          initialQuery.length > 40 ? `${initialQuery.slice(0, 40)}...` : initialQuery;
        const newSession: Session = {
          id,
          title: truncatedTitle,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        set((state) => ({
          sessions: [newSession, ...state.sessions],
          activeSessionId: id,
          turnsBySession: {
            ...state.turnsBySession,
            [id]: [],
          },
        }));
        return newSession;
      },

      rekeySession: (tempId, realId) => {
        if (tempId === realId) return;
        set((state) => {
          const newTurns = { ...state.turnsBySession };
          const movedTurns = newTurns[tempId] || [];
          delete newTurns[tempId];
          newTurns[realId] = [...(newTurns[realId] || []), ...movedTurns];

          const tempSession = state.sessions.find((s) => s.id === tempId);
          const hasRealSession = state.sessions.some((s) => s.id === realId);
          const withoutTemp = state.sessions.filter((s) => s.id !== tempId);
          const newSessions =
            tempSession && !hasRealSession
              ? [{ ...tempSession, id: realId }, ...withoutTemp]
              : withoutTemp;

          return {
            sessions: newSessions,
            turnsBySession: newTurns,
            activeSessionId:
              state.activeSessionId === tempId ? realId : state.activeSessionId,
          };
        });
      },

      renameSession: (id, newTitle) => {
        set((state) => ({
          sessions: state.sessions.map((s) => (s.id === id ? { ...s, title: newTitle } : s)),
        }));
      },

      deleteSession: (id) => {
        set((state) => {
          const newSessions = state.sessions.filter((s) => s.id !== id);
          const newTurns = { ...state.turnsBySession };
          delete newTurns[id];
          return {
            sessions: newSessions,
            turnsBySession: newTurns,
            activeSessionId:
              state.activeSessionId === id ? newSessions[0]?.id || null : state.activeSessionId,
          };
        });
      },

      appendTurn: (sessionId, turn) => {
        set((state) => {
          const sessionTurns = state.turnsBySession[sessionId] || [];
          return {
            turnsBySession: {
              ...state.turnsBySession,
              [sessionId]: [...sessionTurns, turn],
            },
            sessions: state.sessions.map((s) =>
              s.id === sessionId ? { ...s, updatedAt: new Date().toISOString() } : s
            ),
          };
        });
      },

      updateTurn: (sessionId, turnId, patch) => {
        set((state) => {
          const sessionTurns = state.turnsBySession[sessionId] || [];
          return {
            turnsBySession: {
              ...state.turnsBySession,
              [sessionId]: sessionTurns.map((t) => (t.id === turnId ? { ...t, ...patch } : t)),
            },
          };
        });
      },

      setPendingQuery: (query) => set({ pendingQuery: query }),
      clearPendingQuery: () => set({ pendingQuery: null }),
    }),
    {
      name: 'lumen-chat-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
);