"use client"
import { useState } from "react"
import { Check, ChevronRight } from "lucide-react"
import { nodeLabel } from "@/lib/nodes"
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible"
import { cn } from "@/lib/utils"

interface ProgressTraceProps {
  steps: string[]
  isLive: boolean
}

export function ProgressTrace({ steps, isLive }: ProgressTraceProps) {
  const [open, setOpen] = useState(false)
  const currentStep = steps.length > 0 ? steps[steps.length - 1] : null
  const currentLabel = currentStep ? nodeLabel(currentStep) : "Starting"

  if (!isLive) {
    if (steps.length === 0) return null
    return (
      <Collapsible open={open} onOpenChange={setOpen} className="mt-2">
        <CollapsibleTrigger className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors group">
          <ChevronRight
            className={cn(
              "size-3 transition-transform duration-150 ease-[cubic-bezier(0.22,1,0.36,1)]",
              open && "rotate-90",
            )}
          />
          <span>Show steps ({steps.length})</span>
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-2 space-y-1.5 pl-4 border-l border-border text-xs text-muted-foreground">
          {steps.map((step, idx) => (
            <div key={`${step}-${idx}`} className="flex items-center gap-2">
              <Check className="size-3.5 text-muted-foreground shrink-0" />
              <span>{nodeLabel(step)}</span>
            </div>
          ))}
        </CollapsibleContent>
      </Collapsible>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2.5 text-sm" aria-live="polite">
        <span className="size-1.5 rounded-full bg-primary animate-pulse shrink-0" />
        <span className="lumen-shimmer font-medium">{currentLabel}</span>
      </div>

      {steps.length > 0 && (
        <Collapsible open={open} onOpenChange={setOpen}>
          <CollapsibleTrigger className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
            <ChevronRight
              className={cn(
                "size-3 transition-transform duration-150 ease-[cubic-bezier(0.22,1,0.36,1)]",
                open && "rotate-90",
              )}
            />
            <span>Show steps</span>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 space-y-1.5 pl-4 border-l border-border text-xs text-muted-foreground">
            {steps.map((step, idx) => {
              const isLatest = idx === steps.length - 1
              return (
                <div key={`${step}-${idx}`} className="flex items-center gap-2">
                  {isLatest ? (
                    <span className="size-1.5 rounded-full bg-primary shrink-0" />
                  ) : (
                    <Check className="size-3.5 text-muted-foreground shrink-0" />
                  )}
                  <span className={cn(isLatest && "text-foreground font-medium")}>
                    {nodeLabel(step)}
                  </span>
                </div>
              )
            })}
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  )
}
