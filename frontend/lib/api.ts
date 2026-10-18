import type { Session, Usage } from "@/lib/types"

export class AuthRequiredError extends Error {}

export class TokenError extends Error {
  constructor(message: string, public status?: number) {
    super(message)
    this.name = "TokenError"
  }
}

export class NetworkError extends Error {
  constructor(message: string, public url: string) {
    super(message)
    this.name = "NetworkError"
  }
}

let cached: { token: string; userId: string; expiresAt: number } | null = null
export function clearTokenCache() {
  cached = null
}

function apiBase(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL
  if (!raw) throw new Error("NEXT_PUBLIC_API_URL is not set")
  return raw.replace(/\/+$/, "")
}

async function getBackendToken(userId: string, forceRefresh = false): Promise<string> {
  const now = Date.now()
  if (!forceRefresh && cached && cached.userId === userId && cached.expiresAt - now > 30_000) return cached.token

  let res: Response
  try {
    res = await fetch("/api/backend-token", { cache: "no-store" })
  } catch {
    throw new TokenError("Could not reach /api/backend-token")
  }

  if (res.status === 401) throw new AuthRequiredError("Not signed in")
  if (!res.ok) throw new TokenError("Could not get a backend token", res.status)

  const body = (await res.json()) as { token: string; expiresIn: number }
  cached = { token: body.token, userId, expiresAt: now + body.expiresIn * 1000 }
  return body.token
}

export async function apiFetch(path: string, init: RequestInit, userId: string): Promise<Response> {
  const url = `${apiBase()}${path}`
  const send = async (token: string) => {
    try {
      return await fetch(url, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          ...(init.headers as Record<string, string> | undefined),
          Authorization: `Bearer ${token}`,
        },
      })
    } catch (error) {
      if (error instanceof TypeError) {
        console.error("[lumen] network error", { url, error })
        throw new NetworkError("Network error", url)
      }
      throw error
    }
  }

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

export function readUsageHeaders(res: Response): Usage | null {
  const limitStr = res.headers.get("X-RateLimit-Limit")
  const remainingStr = res.headers.get("X-RateLimit-Remaining")
  const resetStr = res.headers.get("X-RateLimit-Reset")
  if (!limitStr || !remainingStr || !resetStr) return null
  const limit = parseInt(limitStr, 10)
  const remaining = parseInt(remainingStr, 10)
  if (isNaN(limit) || isNaN(remaining)) return null
  const used = Math.max(limit - remaining, 0)
  return {
    limit,
    used,
    remaining,
    resetsAt: resetStr,
  }
}

export async function fetchUsage(userId: string): Promise<Usage | null> {
  try {
    const res = await apiFetch("/usage", { method: "GET" }, userId)
    if (!res.ok) return null
    return (await res.json()) as Usage
  } catch {
    return null
  }
}
