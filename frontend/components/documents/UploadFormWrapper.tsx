import { FILE_VALIDATION } from '@/lib/validation/document'
import { UploadFormClient } from './UploadFormClient'

// Server Component - only static labels and structure
export function UploadForm() {
  const acceptedExtensions = FILE_VALIDATION.ACCEPTED_FILE_EXTENSIONS.join(',')

  return (
    <div className="space-y-4 p-6 border rounded-lg">
      <div>
        <label htmlFor="file" className="block text-sm font-medium mb-2">
          Document File *
        </label>
        <p className="text-xs text-muted-foreground mb-2">
          Accepted: PDF, Markdown (.pdf, .md, .markdown) • Max: 50MB
        </p>
      </div>

      <div>
        <label htmlFor="domain" className="block text-sm font-medium mb-2">
          Domain (optional)
        </label>
      </div>

      <div>
        <label htmlFor="description" className="block text-sm font-medium mb-2">
          Description (optional)
        </label>
      </div>

      <UploadFormClient acceptedExtensions={acceptedExtensions} />
    </div>
  )
}
