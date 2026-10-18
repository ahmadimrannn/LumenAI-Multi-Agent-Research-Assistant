"use client"
import { useState } from "react"
import { useSession } from "next-auth/react"
import type { Turn } from "@/lib/types"
import { retryTurn } from "@/lib/chat-actions"
import { LumenMark } from "@/components/lumen-mark"
import { ProgressTrace } from "@/components/progress-trace"
import { ReportView } from "@/components/report-view"
import { ApprovalCard } from "@/components/approval-card"
import { Button } from "@/components/ui/button"

interface TurnViewProps {
  turn: Turn
}

export function TurnView({ turn }: TurnViewProps) {
  const { data: session } = useSession()
  const userId = session?.user?.id ?? ""
  const [wasCompletedOnMount] = useState(() => turn.status === "completed")

  const isForbidden =
    turn.errorMessage?.includes("not available to your account") || false

  const handleRetry = () => {
    if (!userId) return
    void retryTurn(userId, turn.id)
  }

  return (
    <div className="flex flex-col gap-6 w-full">
      {/* 1. User message */}
      <div className="flex flex-col items-end">
        <div className="max-w-[85%] rounded-2xl bg-secondary px-4 py-2.5 text-[15px] leading-relaxed text-foreground select-text">
          <p className="whitespace-pre-wrap">{turn.query}</p>
        </div>
        {turn.editedQuery && (
          <span className="mt-1 text-xs text-muted-foreground mr-1">
            Edited to: {turn.editedQuery}
          </span>
        )}
      </div>

      {/* 2. Assistant block */}
      <div className="flex flex-col gap-3 w-full">
        <div className="flex items-center gap-2 select-none">
          <LumenMark className="size-4 text-primary shrink-0" />
          <span className="font-heading font-medium tracking-tight text-sm text-foreground">
            Lumen
          </span>
        </div>

        <div className="pl-6 w-full">
          {turn.status === "streaming" && (
            <ProgressTrace steps={turn.progressSteps} isLive={true} />
          )}

          {turn.status === "completed" && (
            <ReportView
              turn={turn}
              shouldAnimate={!wasCompletedOnMount}
            />
          )}

          {turn.status === "interrupted" && (
            <ApprovalCard turn={turn} userId={userId} />
          )}

          {turn.status === "terminated" && (
            <div className="rounded-xl border border-border bg-card p-4 space-y-1.5">
              <h4 className="font-heading font-medium tracking-tight text-sm text-foreground">
                Stopped before a report
              </h4>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {turn.terminationReason || "The process finished without generating a report."}
              </p>
            </div>
          )}

          {turn.status === "error" && (
            <div className="rounded-xl border border-border bg-card p-4 space-y-2">
              <div className="text-sm font-medium text-foreground">Something went wrong.</div>
              {turn.errorMessage && (
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {turn.errorMessage}
                </p>
              )}
              {!isForbidden && (
                <div className="pt-1">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-8 px-2.5 text-xs"
                    onClick={handleRetry}
                  >
                    Try again
                  </Button>
                </div>
              )}
            </div>
          )}

          {turn.status === "stopped" && (
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground">Stopped.</span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 px-2.5 text-xs"
                onClick={handleRetry}
              >
                Try again
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
