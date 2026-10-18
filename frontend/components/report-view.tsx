"use client"
import { useState } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { motion } from "motion/react"
import { ChevronRight } from "lucide-react"
import type { Turn } from "@/lib/types"
import { ProgressTrace } from "@/components/progress-trace"
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible"
import { cn } from "@/lib/utils"

interface ReportViewProps {
  turn: Turn
  shouldAnimate: boolean
}

const EASING = [0.22, 1, 0.36, 1] as const

function formatCachedRelativeTime(cachedAt?: string): string {
  if (!cachedAt) return "Answered from a saved result."
  try {
    const diffMs = new Date(cachedAt).getTime() - Date.now()
    const diffHours = Math.round(diffMs / (1000 * 60 * 60))
    const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" })
    if (Math.abs(diffHours) >= 24) {
      const diffDays = Math.round(diffHours / 24)
      return `Answered from a saved result from ${rtf.format(diffDays, "day")}.`
    }
    return `Answered from a saved result from ${rtf.format(diffHours, "hour")}.`
  } catch {
    return "Answered from a saved result."
  }
}

export function ReportView({ turn, shouldAnimate }: ReportViewProps) {
  const [detailsOpen, setDetailsOpen] = useState(false)

  const hasDetails =
    turn.knowledgeSource !== undefined ||
    turn.requiresExternalResearch !== undefined ||
    turn.degraded === true ||
    turn.cached === true

  const content = (
    <div className="flex flex-col gap-4">
      <div className="prose prose-sm dark:prose-invert max-w-none text-foreground leading-relaxed">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            a: ({ ...props }) => (
              <a
                {...props}
                className="text-primary font-medium underline-offset-4 hover:underline"
                target="_blank"
                rel="noreferrer"
              />
            ),
          }}
        >
          {turn.response || ""}
        </ReactMarkdown>
      </div>

      <div className="flex flex-col gap-1 text-xs text-muted-foreground border-t border-border/40 pt-3">
        {hasDetails && (
          <Collapsible open={detailsOpen} onOpenChange={setDetailsOpen}>
            <CollapsibleTrigger className="inline-flex items-center gap-1.5 hover:text-foreground transition-colors">
              <ChevronRight
                className={cn(
                  "size-3 transition-transform duration-150 ease-[cubic-bezier(0.22,1,0.36,1)]",
                  detailsOpen && "rotate-90",
                )}
              />
              <span>Details</span>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2 space-y-1.5 pl-4 border-l border-border text-xs">
              {turn.cached && (
                <div>
                  <span className="text-muted-foreground">
                    {formatCachedRelativeTime(turn.cachedAt)}
                  </span>
                </div>
              )}
              {turn.knowledgeSource && (
                <div>
                  <span className="text-muted-foreground">Knowledge source: </span>
                  <span className="text-foreground">{turn.knowledgeSource}</span>
                </div>
              )}
              {turn.requiresExternalResearch !== undefined && (
                <div>
                  <span className="text-muted-foreground">Used external research: </span>
                  <span className="text-foreground">
                    {turn.requiresExternalResearch ? "yes" : "no"}
                  </span>
                </div>
              )}
              {turn.degraded && (
                <div className="text-muted-foreground">
                  Limited confidence: some steps did not complete cleanly.
                </div>
              )}
            </CollapsibleContent>
          </Collapsible>
        )}

        <ProgressTrace steps={turn.progressSteps} isLive={false} />
      </div>
    </div>
  )

  if (shouldAnimate) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: EASING }}
      >
        {content}
      </motion.div>
    )
  }

  return content
}
