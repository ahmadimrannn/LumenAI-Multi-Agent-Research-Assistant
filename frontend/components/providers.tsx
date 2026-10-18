"use client"
import React from "react"
import type { Session } from "next-auth"
import { SessionProvider } from "next-auth/react"
import { ThemeProvider } from "next-themes"
import { MotionConfig } from "motion/react"
import { TooltipProvider } from "@/components/ui/tooltip"
import { AuthSync } from "@/components/auth-sync"
import { PendingQueryResume } from "@/components/pending-query-resume"
import { SignInDialog } from "@/components/sign-in-dialog"

interface ProvidersProps {
  children: React.ReactNode
  session: Session | null
}

export function Providers({ children, session }: ProvidersProps) {
  return (
    <SessionProvider session={session}>
      <ThemeProvider
        attribute="class"
        defaultTheme="dark"
        enableSystem={false}
        disableTransitionOnChange
      >
        <MotionConfig reducedMotion="user">
          <TooltipProvider>
            {children}
            <AuthSync />
            <PendingQueryResume />
            <SignInDialog />
          </TooltipProvider>
        </MotionConfig>
      </ThemeProvider>
    </SessionProvider>
  )
}
