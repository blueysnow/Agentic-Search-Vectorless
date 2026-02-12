import Link from 'next/link'

export default function Dashboard() {
  return (
    <div className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link
          href="/documents"
          className="p-6 border rounded-lg hover:border-primary transition-colors"
        >
          <h2 className="text-xl font-semibold mb-2">Documents</h2>
          <p className="text-muted-foreground">
            Upload and manage your documents
          </p>
        </Link>
        <Link
          href="/query"
          className="p-6 border rounded-lg hover:border-primary transition-colors"
        >
          <h2 className="text-xl font-semibold mb-2">Query</h2>
          <p className="text-muted-foreground">
            Ask questions about your documents
          </p>
        </Link>
        <Link
          href="/sessions"
          className="p-6 border rounded-lg hover:border-primary transition-colors"
        >
          <h2 className="text-xl font-semibold mb-2">Sessions</h2>
          <p className="text-muted-foreground">
            View your conversation history
          </p>
        </Link>
      </div>
    </div>
  )
}
