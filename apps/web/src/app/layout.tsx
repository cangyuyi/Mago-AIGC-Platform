import type { Metadata } from "next";
import "@/styles/globals.css";
import { ThemeProvider } from "next-themes";

export const metadata: Metadata = {
  title: "Mago - AI创意Agent平台",
  description: "从灵感到提示词，AI驱动的短视频创意工厂",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body className="min-h-screen bg-background">
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
