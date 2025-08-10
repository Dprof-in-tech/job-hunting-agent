import './globals.css'
import { Inter } from 'next/font/google'
import { Analytics } from "@vercel/analytics/next"

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'Intelligent Career Assistant',
  description: 'AI-powered job hunting with autonomous multi-agent coordination. Upload your resume and describe what you need—our specialists will handle the rest',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}<Analytics /></body>
    </html>
  )
}
