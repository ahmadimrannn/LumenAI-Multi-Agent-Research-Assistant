"use client"
import { useSyncExternalStore } from "react"
import { useTheme } from "next-themes"
import { motion, AnimatePresence } from "motion/react"
import { Sun, Moon } from "lucide-react"
import { Button } from "@/components/ui/button"

const EASING = [0.22, 1, 0.36, 1] as const
const emptySubscribe = () => () => {}

export function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme()
  const mounted = useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  )

  if (!mounted) {
    return (
      <Button
        variant="ghost"
        size="icon"
        className="size-9"
        aria-label="Switch to light theme"
        disabled
      >
        <span className="size-4" />
      </Button>
    )
  }

  const currentTheme = theme === "system" ? resolvedTheme : theme
  const isDark = currentTheme === "dark"

  const toggleTheme = () => {
    setTheme(isDark ? "light" : "dark")
  }

  const ariaLabel = isDark ? "Switch to light theme" : "Switch to dark theme"

  return (
    <Button
      variant="ghost"
      size="icon"
      className="size-9"
      onClick={toggleTheme}
      aria-label={ariaLabel}
    >
      <AnimatePresence mode="wait" initial={false}>
        {isDark ? (
          <motion.div
            key="moon"
            initial={{ opacity: 0, rotate: -60 }}
            animate={{ opacity: 1, rotate: 0 }}
            exit={{ opacity: 0, rotate: 60 }}
            transition={{ duration: 0.18, ease: EASING }}
            className="flex items-center justify-center"
          >
            <Moon className="size-4" />
          </motion.div>
        ) : (
          <motion.div
            key="sun"
            initial={{ opacity: 0, rotate: 60 }}
            animate={{ opacity: 1, rotate: 0 }}
            exit={{ opacity: 0, rotate: -60 }}
            transition={{ duration: 0.18, ease: EASING }}
            className="flex items-center justify-center"
          >
            <Sun className="size-4" />
          </motion.div>
        )}
      </AnimatePresence>
    </Button>
  )
}
