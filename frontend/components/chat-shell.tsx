"use client"
import React from "react"
import { useSession } from "next-auth/react"
import { useChatStore, NEW_CHAT_KEY } from "@/store/chat-store"
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/app-sidebar"
import { ChatHeader } from "@/components/chat-header"
import { EmptyState } from "@/components/empty-state"
import { Thread } from "@/components/thread"

export function ChatShell() {
  const { data: session } = useSession()
  const isSignedIn = !!session?.user?.id

  const activeSessionId = useChatStore((s) => s.activeSessionId)
  const turnsBySession = useChatStore((s) => s.turnsBySession)

  const currentKey = activeSessionId ?? NEW_CHAT_KEY
  const turns = turnsBySession[currentKey] ?? []
  const isEmpty = activeSessionId === null && turns.length === 0

  if (!isSignedIn) {
    return (
      <div className="flex flex-col h-dvh w-full overflow-hidden bg-background bg-[radial-gradient(60%_40%_at_50%_0%,color-mix(in_oklab,var(--primary)_7%,transparent),transparent)]">
        <ChatHeader />
        <main className="flex-1 flex flex-col overflow-hidden">
          {isEmpty ? <EmptyState /> : <Thread turns={turns} />}
        </main>
      </div>
    )
  }

  return (
    <SidebarProvider
      style={{ "--sidebar-width": "17rem" } as React.CSSProperties}
      className="h-dvh overflow-hidden"
    >
      <AppSidebar />
      <SidebarInset className="flex flex-col h-dvh w-full overflow-hidden bg-background bg-[radial-gradient(60%_40%_at_50%_0%,color-mix(in_oklab,var(--primary)_7%,transparent),transparent)]">
        <ChatHeader />
        <main className="flex-1 flex flex-col overflow-hidden">
          {isEmpty ? <EmptyState /> : <Thread turns={turns} />}
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
