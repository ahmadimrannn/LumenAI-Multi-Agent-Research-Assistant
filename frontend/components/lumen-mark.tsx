import Image from "next/image"
import { cn } from "@/lib/utils"

export function LumenMark({ className }: { className?: string }) {
  return (
    <Image
      src="/logo.png"
      alt="Lumen"
      width={24}
      height={24}
      className={cn("size-4 object-contain shrink-0", className)}
      priority
    />
  )
}
