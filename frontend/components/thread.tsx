"use client"
import { useRef, useEffect } from "react"
import type { Turn } from "@/lib/types"
import { TurnView } from "@/components/turn-view"
import { Composer } from "@/components/composer"

interface ThreadProps {
  turns: Turn[]
}

export function Thread({ turns }: ThreadProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const isNearBottomRef = useRef(true)

  const handleScroll = () => {
    if (!scrollRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight
    isNearBottomRef.current = distanceFromBottom <= 120
  }

  useEffect(() => {
    if (isNearBottomRef.current && scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      })
    }
  }, [turns])

  const hasTurns = turns.length > 0

  return (
    <div className="flex flex-1 flex-col h-full overflow-hidden relative">
      {/* Scrollable messages area */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-4 pt-6 pb-4"
      >
        <div className="mx-auto w-full max-w-3xl flex flex-col gap-8">
          {hasTurns ? (
            turns.map((turn) => <TurnView key={turn.id} turn={turn} />)
          ) : (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <p className="text-sm text-muted-foreground max-w-md leading-relaxed">
                Earlier messages in this conversation are not available on this device. You can still continue it.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Docked composer */}
      <div className="w-full shrink-0 px-4 pt-2 pb-[max(1rem,env(safe-area-inset-bottom))] bg-gradient-to-t from-background via-background/95 to-transparent">
        <div className="mx-auto w-full max-w-3xl">
          <Composer isDocked={true} />
        </div>
      </div>
    </div>
  )
}
