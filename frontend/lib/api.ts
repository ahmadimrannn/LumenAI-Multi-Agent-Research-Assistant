import type { Session } from "@/lib/types"

const API_URL = process.env.NEXT_PUBLIC_API_URL!

export class AuthRequiredError extends Error {}

let cached: { token: string; userId: string; expiresAt: number } | null = null
export function clearTokenCache() {
  cached = null
}

async function getBackendToken(userId: string, forceRefresh = false): Promise<string> {
  const now = Date.now()
  if (!forceRefresh && cached && cached.userId === userId && cached.expiresAt - now > 30_000) return cached.token
  const res = await fetch("/api/backend-token", { cache: "no-store" })
  if (res.status === 401) throw new AuthRequiredError("Not signed in")
  if (!res.ok) throw new Error("Could not get a backend token")
  const body = (await res.json()) as { token: string; expiresIn: number }
  cached = { token: body.token, userId, expiresAt: now + body.expiresIn * 1000 }
  return body.token
}

export async function apiFetch(path: string, init: RequestInit, userId: string): Promise<Response> {
  const send = (token: string) =>
    fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init.headers as Record<string, string> | undefined),
        Authorization: `Bearer ${token}`,
      },
    })
  let res = await send(await getBackendToken(userId))
  if (res.status === 401) res = await send(await getBackendToken(userId, true))
  return res
}

export async function fetchSessions(userId: string): Promise<Session[]> {
  const res = await apiFetch("/sessions", { method: "GET" }, userId)
  if (!res.ok) throw new Error(`Sessions request failed with ${res.status}`)
  const body = (await res.json()) as { sessions: Session[] }
  return body.sessions
}
