"use client"
import { Composer } from "@/components/composer"

export function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 -mt-12 w-full">
      <div className="flex flex-col items-center text-center max-w-xl mx-auto w-full mb-8">
        <h1 className="font-heading font-medium tracking-tighter text-5xl sm:text-6xl text-foreground">
          Lumen
        </h1>
        <p className="mt-3 text-base text-muted-foreground max-w-[28rem] leading-relaxed">
          Ask a question. Lumen researches it, checks the sources, and writes it up.
        </p>
      </div>
      <div className="w-full max-w-2xl">
        <Composer isDocked={false} />
      </div>
    </div>
  )
}
