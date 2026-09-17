import type { Metadata } from "next";
import { Geist, Inter } from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip"
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

const geist = Geist({
    variable: "--font-geist",
    subsets: ["latin"],
});

const inter = Inter({
    variable: "--font-inter",
    subsets: ["latin"],
});


export const metadata: Metadata = {
    title: "Lumen - Multi Agent Research Assistant",
    description: "A multi agent research assitant",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
    return (
        <html
            lang="en"
            className={`${geist.variable} ${inter.variable} h-full antialiased`}
            suppressHydrationWarning
        >
            <body className="min-h-full flex flex-col" suppressHydrationWarning>
                <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
                    <TooltipProvider>
                        {children}
                    </TooltipProvider>
                </ThemeProvider>
            </body>
        </html>
    );
}
