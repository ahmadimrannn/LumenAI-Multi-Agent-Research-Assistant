"use client"
import React, { useState, useRef, useEffect } from "react"
import { useSession } from "next-auth/react"
import { motion } from "motion/react"
import { ArrowUp, Square } from "lucide-react"
import { useChatStore, NEW_CHAT_KEY } from "@/store/chat-store"
import { sendMessage, requestSignIn } from "@/lib/chat-actions"
import { cn } from "@/lib/utils"

interface ComposerProps {
  isDocked?: boolean
  className?: string
}

export function Composer({ isDocked = false, className }: ComposerProps) {
  const [query, setQuery] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const { data: session } = useSession()
  const userId = session?.user?.id ?? null

  const activeStreams = useChatStore((s) => s.activeStreams)
  const activeSessionId = useChatStore((s) => s.activeSessionId)
  const turnsBySession = useChatStore((s) => s.turnsBySession)
  const abortTurn = useChatStore((s) => s.abortTurn)
  const abortAll = useChatStore((s) => s.abortAll)

  const isStreaming = activeStreams > 0

  const key = activeSessionId ?? NEW_CHAT_KEY
  const turns = turnsBySession[key] ?? []
  const runningTurn = turns.find((t) => t.status === "streaming")

  // Auto-resize textarea up to ~160px
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      const nextHeight = Math.min(textareaRef.current.scrollHeight, 160)
      textareaRef.current.style.height = `${nextHeight}px`
    }
  }, [query])

  const handleSend = () => {
    const text = query.trim()
    if (!text || isStreaming) return
    if (!userId) {
      requestSignIn(text)
    } else {
      setQuery("")
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto"
      }
      void sendMessage(text, userId)
    }
  }

  const handleStop = () => {
    if (runningTurn) {
      abortTurn(runningTurn.id)
    } else {
      abortAll()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className={cn("w-full flex flex-col items-center", className)}>
      <motion.div
        layoutId="composer-surface"
        transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
        className="w-full rounded-2xl border border-border bg-card p-2.5 transition-[border-color,box-shadow] duration-200 focus-within:border-primary/40 focus-within:ring-4 focus-within:ring-primary/10"
      >
        <div className="flex flex-col gap-2">
          <textarea
            ref={textareaRef}
            rows={1}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask Lumen to research anything"
            className="w-full resize-none border-0 bg-transparent px-2.5 py-1.5 text-sm sm:text-[15px] leading-relaxed text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-0 max-h-[160px] overflow-y-auto"
          />
          <div className="flex items-center justify-end px-1">
            {isStreaming ? (
              <button
                type="button"
                onClick={handleStop}
                aria-label="Stop"
                className="size-9 rounded-full bg-primary text-primary-foreground flex items-center justify-center transition-transform active:scale-[0.97] hover:opacity-90"
              >
                <Square className="size-3.5 fill-current" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSend}
                disabled={!query.trim()}
                aria-label="Send message"
                className="size-9 rounded-full bg-primary text-primary-foreground flex items-center justify-center transition-all disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.97] hover:opacity-90"
              >
                <ArrowUp className="size-4 stroke-[2.2]" />
              </button>
            )}
          </div>
        </div>
      </motion.div>
      {isDocked && (
        <p className="mt-2 text-center text-xs text-muted-foreground select-none">
          Lumen can make mistakes. Check anything important.
        </p>
      )}
    </div>
  )
}
