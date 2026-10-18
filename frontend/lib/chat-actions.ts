import { useChatStore, NEW_CHAT_KEY } from "@/store/chat-store"
import { apiFetch, fetchSessions, AuthRequiredError } from "@/lib/api"
import { readEvents } from "@/lib/sse"
import type { LumenEvent, Turn } from "@/lib/types"

export const PENDING_KEY = "lumen:pending-query"

type Run =
  | { kind: "research"; query: string; threadId: string | null }
  | { kind: "resume"; threadId: string; action: "approve" | "reject" | "edit"; editedQuery?: string }

const store = () => useChatStore.getState()

function handleEvent(key: string, turnId: string, event: LumenEvent, fail: (m: string) => void): boolean {
  switch (event.type) {
    case "node_update":
      for (const node of Object.keys(event.data ?? {})) {
        if (!node.startsWith("__")) store().addProgressStep(key, turnId, node)
      }
      return false
    case "interrupted":
      store().updateTurn(key, turnId, { status: "interrupted", interrupt: event.interrupt, errorMessage: undefined })
      return true
    case "completed": {
      const response = (event.response ?? "").trim()
      if (!response && event.termination_reason) {
        store().updateTurn(key, turnId, {
          status: "terminated",
          terminationReason: event.termination_reason,
          interrupt: undefined,
        })
      } else {
        store().updateTurn(key, turnId, {
          status: "completed",
          response,
          knowledgeSource: event.knowledge_source,
          requiresExternalResearch: event.requires_external_research,
          degraded: event.degraded,
          interrupt: undefined,
          errorMessage: undefined,
        })
      }
      return true
    }
    case "error":
      fail(event.error || "Something went wrong.")
      return true
    default:
      return false
  }
}

async function runTurn(userId: string, sessionKey: string, turnId: string, run: Run, firstQuery: string) {
  const controller = new AbortController()
  store().registerController(turnId, controller)
  let key = sessionKey

  const fail = (message: string) => {
    if (run.kind === "resume") store().updateTurn(key, turnId, { status: "interrupted", errorMessage: message })
    else store().updateTurn(key, turnId, { status: "error", errorMessage: message })
  }

  try {
    const res =
      run.kind === "research"
        ? await apiFetch(
            "/research",
            {
              method: "POST",
              signal: controller.signal,
              body: JSON.stringify({ query: run.query, ...(run.threadId ? { thread_id: run.threadId } : {}) }),
            },
            userId,
          )
        : await apiFetch(
            "/research/resume",
            {
              method: "POST",
              signal: controller.signal,
              body: JSON.stringify({
                thread_id: run.threadId,
                action: run.action,
                ...(run.action === "edit" ? { edited_query: run.editedQuery } : {}),
              }),
            },
            userId,
          )

    if (!res.ok) {
      if (res.status === 401) {
        store().setSignInOpen(true)
        fail("Your session expired. Sign in again.")
      } else if (res.status === 403) {
        fail("This conversation is not available to your account.")
      } else {
        let detail = ""
        try {
          const b = await res.json()
          if (typeof b?.detail === "string") detail = b.detail
        } catch {}
        fail(detail || "The server could not process this request.")
      }
      return
    }

    let finished = false
    for await (const event of readEvents(res)) {
      if (event.thread_id && key === NEW_CHAT_KEY) {
        store().adoptThread(event.thread_id, firstQuery)
        key = event.thread_id
      }
      if (handleEvent(key, turnId, event, fail)) finished = true
    }
    if (!finished) fail("The connection closed before the answer finished.")
  } catch (err) {
    if (err instanceof AuthRequiredError) {
      store().setSignInOpen(true)
      fail("Sign in to continue.")
    } else if (controller.signal.aborted) {
      if (run.kind === "resume") store().updateTurn(key, turnId, { status: "interrupted", errorMessage: "Stopped." })
      else store().updateTurn(key, turnId, { status: "stopped" })
    } else {
      fail("Could not reach the server. Check your connection and try again.")
    }
  } finally {
    store().releaseController(turnId)
    if (key !== NEW_CHAT_KEY) store().touchSession(key)
    void fetchSessions(userId)
      .then((list) => store().mergeServerSessions(list))
      .catch(() => {})
  }
}

export async function sendMessage(query: string, userId: string) {
  const text = query.trim()
  const s = store()
  if (!text || s.activeStreams > 0) return
  const key = s.activeSessionId ?? NEW_CHAT_KEY
  const turn: Turn = { id: crypto.randomUUID(), query: text, status: "streaming", progressSteps: [] }
  s.appendTurn(key, turn)
  await runTurn(userId, key, turn.id, { kind: "research", query: text, threadId: s.activeSessionId }, text)
}

export async function resumeTurn(
  userId: string,
  turnId: string,
  action: "approve" | "reject" | "edit",
  editedQuery?: string,
) {
  const s = store()
  const key = s.activeSessionId
  if (!key || s.activeStreams > 0) return
  s.updateTurn(key, turnId, {
    status: "streaming",
    errorMessage: undefined,
    ...(action === "edit" ? { editedQuery } : {}),
  })
  await runTurn(userId, key, turnId, { kind: "resume", threadId: key, action, editedQuery }, "")
}

export async function retryTurn(userId: string, turnId: string) {
  const s = store()
  const key = s.activeSessionId ?? NEW_CHAT_KEY
  const turn = s.turnsBySession[key]?.find((t) => t.id === turnId)
  if (!turn || s.activeStreams > 0) return
  s.updateTurn(key, turnId, {
    status: "streaming",
    progressSteps: [],
    errorMessage: undefined,
    response: undefined,
    terminationReason: undefined,
  })
  await runTurn(userId, key, turnId, { kind: "research", query: turn.query, threadId: s.activeSessionId }, turn.query)
}

export function requestSignIn(draft: string) {
  sessionStorage.setItem(PENDING_KEY, draft)
  store().setSignInOpen(true)
}
