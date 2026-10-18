"use client"
import { useEffect } from "react"
import { useSession } from "next-auth/react"
import { useChatStore } from "@/store/chat-store"
import { sendMessage, PENDING_KEY } from "@/lib/chat-actions"

export function PendingQueryResume() {
  const { data: session } = useSession()
  const userId = session?.user?.id ?? null
  const hydrated = useChatStore((s) => s.hydrated)

  useEffect(() => {
    if (!userId || !hydrated) return
    const pending = sessionStorage.getItem(PENDING_KEY)
    if (pending) {
      sessionStorage.removeItem(PENDING_KEY)
      void sendMessage(pending, userId)
    }
  }, [userId, hydrated])

  return null
}
