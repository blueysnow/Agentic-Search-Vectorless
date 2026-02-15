import type { Metadata } from 'next'
import localFont from 'next/font/local'
import './globals.css'
import { Providers } from './providers'
import { Toaster } from '@/components/ui/toaster'
import { AppShell } from '@/components/layout/AppShell'

const inter = localFont({
  src: '../public/fonts/Inter-Variable.ttf',
  variable: '--font-inter',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Vectorless RAG System',
  description: 'Document ingestion and querying with PageIndex Trees',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
        <Toaster />
      </body>
    </html>
  )
}
