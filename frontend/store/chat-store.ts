"use client"
import { create } from "zustand"
import { persist, createJSONStorage, type StateStorage } from "zustand/middleware"
import type { Session, Turn, Usage } from "@/lib/types"

export const NEW_CHAT_KEY = "__new__"

let storageUserId: string | null = null
export function setStorageUser(id: string | null) {
  storageUserId = id
}

const userScopedStorage: StateStorage = {
  getItem: (name) => (storageUserId ? localStorage.getItem(`${name}:${storageUserId}`) : null),
  setItem: (name, value) => {
    if (storageUserId) localStorage.setItem(`${name}:${storageUserId}`, value)
  },
  removeItem: (name) => {
    if (storageUserId) localStorage.removeItem(`${name}:${storageUserId}`)
  },
}

const controllers = new Map<string, AbortController>()

interface ChatState {
  sessions: Session[]
  turnsBySession: Record<string, Turn[]>
  activeSessionId: string | null
  hydrated: boolean
  signInOpen: boolean
  activeStreams: number
  usage: Usage | null

  setActiveSession: (id: string | null) => void
  setSignInOpen: (open: boolean) => void
  setUsage: (u: Usage | null) => void
  appendTurn: (key: string, turn: Turn) => void
  updateTurn: (key: string, turnId: string, patch: Partial<Turn>) => void
  addProgressStep: (key: string, turnId: string, node: string) => void
  adoptThread: (threadId: string, title: string) => void
  mergeServerSessions: (list: Session[]) => void
  touchSession: (id: string) => void
  normalizeStaleStreams: () => void
  resetInMemory: () => void
  registerController: (turnId: string, controller: AbortController) => void
  releaseController: (turnId: string) => void
  abortTurn: (turnId: string) => void
  abortAll: () => void
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      sessions: [],
      turnsBySession: {},
      activeSessionId: null,
      hydrated: false,
      signInOpen: false,
      activeStreams: 0,
      usage: null,

      setActiveSession: (id) => set({ activeSessionId: id }),
      setSignInOpen: (open) => set({ signInOpen: open }),
      setUsage: (u) => set({ usage: u }),

      appendTurn: (key, turn) =>
        set((s) => ({
          turnsBySession: {
            ...s.turnsBySession,
            [key]: [...(s.turnsBySession[key] ?? []), turn],
          },
        })),

      updateTurn: (key, turnId, patch) =>
        set((s) => {
          const list = s.turnsBySession[key]
          if (!list) return s
          return {
            turnsBySession: {
              ...s.turnsBySession,
              [key]: list.map((t) => (t.id === turnId ? { ...t, ...patch } : t)),
            },
          }
        }),

      addProgressStep: (key, turnId, node) =>
        set((s) => {
          const list = s.turnsBySession[key]
          if (!list) return s
          return {
            turnsBySession: {
              ...s.turnsBySession,
              [key]: list.map((t) =>
                t.id === turnId ? { ...t, progressSteps: [...t.progressSteps, node] } : t,
              ),
            },
          }
        }),

      adoptThread: (threadId, title) =>
        set((s) => {
          const moved = s.turnsBySession[NEW_CHAT_KEY] ?? []
          const rest = { ...s.turnsBySession }
          delete rest[NEW_CHAT_KEY]
          const now = new Date().toISOString()
          const exists = s.sessions.some((x) => x.id === threadId)
          return {
            turnsBySession: { ...rest, [threadId]: [...(rest[threadId] ?? []), ...moved] },
            sessions: exists
              ? s.sessions
              : [{ id: threadId, title: title.slice(0, 120), createdAt: now, updatedAt: now }, ...s.sessions],
            activeSessionId: s.activeSessionId === null ? threadId : s.activeSessionId,
          }
        }),

      mergeServerSessions: (list) =>
        set((s) => {
          const byId = new Map(s.sessions.map((x) => [x.id, x]))
          for (const item of list) byId.set(item.id, item)
          const merged = [...byId.values()].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
          return { sessions: merged }
        }),

      touchSession: (id) =>
        set((s) => ({
          sessions: s.sessions
            .map((x) => (x.id === id ? { ...x, updatedAt: new Date().toISOString() } : x))
            .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
        })),

      normalizeStaleStreams: () =>
        set((s) => {
          const next: Record<string, Turn[]> = {}
          for (const [key, list] of Object.entries(s.turnsBySession)) {
            next[key] = list.map((t) =>
              t.status === "streaming"
                ? {
                    ...t,
                    status: "error" as const,
                    errorMessage: "This answer was cut off when the page closed. Try again.",
                  }
                : t,
            )
          }
          return { turnsBySession: next }
        }),

      resetInMemory: () =>
        set({
          sessions: [],
          turnsBySession: {},
          activeSessionId: null,
          hydrated: false,
          signInOpen: false,
          usage: null,
        }),

      registerController: (turnId, controller) => {
        controllers.set(turnId, controller)
        set({ activeStreams: controllers.size })
      },
      releaseController: (turnId) => {
        controllers.delete(turnId)
        set({ activeStreams: controllers.size })
      },
      abortTurn: (turnId) => {
        controllers.get(turnId)?.abort()
      },
      abortAll: () => {
        controllers.forEach((c) => c.abort())
        controllers.clear()
        set({ activeStreams: 0 })
      },
    }),
    {
      name: "lumen-chat",
      version: 1,
      storage: createJSONStorage(() => userScopedStorage),
      partialize: (s) => ({ sessions: s.sessions, turnsBySession: s.turnsBySession }),
      skipHydration: true,
    },
  ),
)
