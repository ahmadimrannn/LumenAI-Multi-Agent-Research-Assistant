"use client"
import { useState } from "react"
import { ChevronRight } from "lucide-react"
import type { Turn } from "@/lib/types"
import { resumeTurn } from "@/lib/chat-actions"
import { useChatStore } from "@/store/chat-store"
import { Button } from "@/components/ui/button"
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible"
import { cn } from "@/lib/utils"

interface ApprovalCardProps {
  turn: Turn
  userId: string
}

export function ApprovalCard({ turn, userId }: ApprovalCardProps) {
  const [editing, setEditing] = useState(false)
  const [editText, setEditText] = useState(turn.editedQuery ?? turn.query)
  const [detailsOpen, setDetailsOpen] = useState(false)

  const activeStreams = useChatStore((s) => s.activeStreams)
  const usage = useChatStore((s) => s.usage)
  const isBusy = activeStreams > 0
  const isLimitReached = Boolean(usage && usage.remaining === 0)

  const handleApprove = () => {
    if (isBusy) return
    void resumeTurn(userId, turn.id, "approve")
  }

  const handleReject = () => {
    if (isBusy) return
    void resumeTurn(userId, turn.id, "reject")
  }

  const handleSubmitEdit = () => {
    const trimmed = editText.trim()
    if (!trimmed || isBusy) return
    void resumeTurn(userId, turn.id, "edit", trimmed)
  }

  const renderPayload = () => {
    const payload = turn.interrupt
    if (!payload) return null

    if (typeof payload === "string") {
      return <p className="text-sm leading-relaxed text-foreground">{payload}</p>
    }

    if (typeof payload === "object" && !Array.isArray(payload)) {
      const stringEntries = Object.entries(payload as Record<string, unknown>).filter(
        ([, v]) => typeof v === "string",
      ) as [string, string][]

      if (stringEntries.length > 0) {
        return (
          <div className="space-y-3">
            {stringEntries.map(([k, v]) => (
              <div key={k} className="space-y-0.5">
                <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                  {k.replace(/_/g, " ")}
                </div>
                <div className="text-sm leading-relaxed text-foreground">{v}</div>
              </div>
            ))}
          </div>
        )
      }
    }

    return (
      <Collapsible open={detailsOpen} onOpenChange={setDetailsOpen} className="text-xs">
        <CollapsibleTrigger className="inline-flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors">
          <ChevronRight
            className={cn(
              "size-3 transition-transform duration-150 ease-[cubic-bezier(0.22,1,0.36,1)]",
              detailsOpen && "rotate-90",
            )}
          />
          <span>Details</span>
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-2 p-2 bg-muted rounded-md overflow-x-auto text-[11px] font-mono text-muted-foreground">
          <pre>{JSON.stringify(payload, null, 2)}</pre>
        </CollapsibleContent>
      </Collapsible>
    )
  }

  return (
    <div className="w-full rounded-xl border border-border bg-card p-4 space-y-4 shadow-none">
      <div className="space-y-1">
        <h3 className="font-heading font-medium tracking-tight text-base text-foreground">
          Approval needed
        </h3>
      </div>

      <div className="space-y-3">{renderPayload()}</div>

      {turn.errorMessage && (
        <p className="text-xs text-muted-foreground">{turn.errorMessage}</p>
      )}

      {editing ? (
        <div className="space-y-3 pt-1">
          <textarea
            rows={3}
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            disabled={isBusy}
            placeholder="Edit your query"
            className="w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <div className="flex items-center gap-2">
            <Button
              type="button"
              size="sm"
              disabled={isBusy || !editText.trim()}
              onClick={handleSubmitEdit}
            >
              Submit edit
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={isBusy}
              onClick={() => {
                setEditing(false)
                setEditText(turn.editedQuery ?? turn.query)
              }}
            >
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <Button
            type="button"
            size="sm"
            disabled={isBusy}
            onClick={handleApprove}
          >
            Approve
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={isBusy}
            onClick={handleReject}
          >
            Reject
          </Button>
          <span
            className={isLimitReached ? "inline-block cursor-not-allowed" : "inline-block"}
            title={isLimitReached ? "Editing counts as a new query and your daily limit is reached." : undefined}
          >
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={isBusy || isLimitReached}
              onClick={() => setEditing(true)}
            >
              Edit
            </Button>
          </span>
        </div>
      )}
    </div>
  )
}
