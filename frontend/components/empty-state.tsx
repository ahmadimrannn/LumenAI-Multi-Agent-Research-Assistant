"use client"
import Image from "next/image"
import { Composer } from "@/components/composer"

export function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 -mt-12 w-full">
      <div className="flex flex-col items-center text-center max-w-2xl mx-auto w-full mb-8">
        <h1 className="flex flex-wrap items-center justify-center gap-3 sm:gap-4 font-heading font-medium tracking-tight text-3xl sm:text-5xl text-foreground">
          <Image
            src="/logo.png"
            alt="Lumen Logo"
            width={52}
            height={52}
            className="size-10 sm:size-12 object-contain shrink-0"
            priority
          />
          <span>Let&apos;s ace your research!</span>
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
