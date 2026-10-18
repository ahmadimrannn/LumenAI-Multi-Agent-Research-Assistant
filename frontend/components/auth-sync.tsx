"use client"
import { useEffect, useRef } from "react"
import { useSession } from "next-auth/react"
import { useChatStore, setStorageUser } from "@/store/chat-store"
import { clearTokenCache, fetchSessions } from "@/lib/api"

export function AuthSync() {
  const { data: session } = useSession()
  const userId = session?.user?.id ?? null
  const previous = useRef<string | null | undefined>(undefined)
  const latestRun = useRef(0)

  useEffect(() => {
    if (previous.current === userId) return
    const isFirstRun = previous.current === undefined
    previous.current = userId
    const runId = ++latestRun.current

    const run = async () => {
      const store = useChatStore.getState()
      if (!isFirstRun) {
        store.abortAll()
        clearTokenCache()
      }
      setStorageUser(null)
      store.resetInMemory()
      if (!userId) return
      setStorageUser(userId)
      await useChatStore.persist.rehydrate()
      if (runId !== latestRun.current) return
      useChatStore.getState().normalizeStaleStreams()
      useChatStore.setState({ hydrated: true })
      try {
        const list = await fetchSessions(userId)
        if (runId === latestRun.current) useChatStore.getState().mergeServerSessions(list)
      } catch {}
    }
    void run()
  }, [userId])

  return null
}
