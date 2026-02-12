import Link from 'next/link'

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-center font-mono text-sm">
        <h1 className="text-4xl font-bold mb-8 text-center">
          Vectorless RAG System
        </h1>
        <p className="text-center text-muted-foreground mb-8">
          Document ingestion and querying with PageIndex Trees
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/dashboard"
            className="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-opacity"
          >
            Go to Dashboard
          </Link>
        </div>
      </div>
    </main>
  )
}
