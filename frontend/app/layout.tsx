import type { Metadata } from "next"
import { Manrope, Geist } from "next/font/google"
import { auth } from "@/auth"
import { Providers } from "@/components/providers"
import "./globals.css"

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope",
  display: "swap",
})

const geist = Geist({
  subsets: ["latin"],
  variable: "--font-geist",
  display: "swap",
})

export const metadata: Metadata = {
  title: "Lumen",
  description: "Research agent that investigates topics, checks sources, and writes reports.",
  icons: {
    icon: "/logo.png",
  },
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const session = await auth()

  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${manrope.variable} ${geist.variable}`}
    >
      <body className="font-sans antialiased bg-background text-foreground">
        <Providers session={session}>{children}</Providers>
      </body>
    </html>
  )
}
