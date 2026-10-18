"use client"
import { useSession } from "next-auth/react"
import { useChatStore } from "@/store/chat-store"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { ThemeToggle } from "@/components/theme-toggle"
import { Button } from "@/components/ui/button"

export function ChatHeader() {
  const { data: session } = useSession()
  const isSignedIn = !!session?.user?.id

  const activeSessionId = useChatStore((s) => s.activeSessionId)
  const sessions = useChatStore((s) => s.sessions)
  const setSignInOpen = useChatStore((s) => s.setSignInOpen)

  const activeSession = sessions.find((s) => s.id === activeSessionId)
  const title = activeSession?.title ?? ""

  const handleSignInClick = () => {
    setSignInOpen(true)
  }

  return (
    <header className="h-14 w-full shrink-0 border-b border-border px-4 flex items-center justify-between gap-4 select-none">
      <div className="flex items-center gap-3 overflow-hidden min-w-0">
        {isSignedIn && <SidebarTrigger aria-label="Toggle sidebar" />}
        {activeSessionId && title && (
          <h2 className="font-heading text-sm font-medium tracking-tight truncate text-foreground">
            {title}
          </h2>
        )}
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {!isSignedIn && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleSignInClick}
            className="text-sm font-sans"
          >
            Sign in
          </Button>
        )}
        <ThemeToggle />
      </div>
    </header>
  )
}
