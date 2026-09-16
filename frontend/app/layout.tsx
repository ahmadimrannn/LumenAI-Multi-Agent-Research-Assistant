import type { Metadata } from "next";
import { Geist } from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip"
import "./globals.css";

const geist = Geist({
    variable: "--font-geist-sans",
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
            className={`${geist.variable} h-full antialiased`}
        >
            <body className="min-h-full flex flex-col">
                <TooltipProvider>
                    {children}
                </TooltipProvider>
            </body>
        </html>
    );
}
