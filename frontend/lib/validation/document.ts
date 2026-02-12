import { z } from 'zod'

const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50MB
const ACCEPTED_FILE_TYPES = ['application/pdf', 'text/markdown']
const ACCEPTED_FILE_EXTENSIONS = ['.pdf', '.md', '.markdown']

export const documentUploadSchema = z.object({
  file: z
    .custom<File>()
    .refine((file) => file instanceof File, 'File is required')
    .refine(
      (file) => file.size <= MAX_FILE_SIZE,
      `File size must be less than 50MB`
    )
    .refine(
      (file) => {
        const hasValidType = ACCEPTED_FILE_TYPES.includes(file.type)
        const hasValidExtension = ACCEPTED_FILE_EXTENSIONS.some((ext) =>
          file.name.toLowerCase().endsWith(ext)
        )
        return hasValidType || hasValidExtension
      },
      'File must be PDF or Markdown (.pdf, .md, .markdown)'
    ),
  domain: z.string().optional(),
  description: z.string().optional(),
})

export type DocumentUploadInput = z.infer<typeof documentUploadSchema>

export function sanitizeFilename(filename: string): string {
  // Remove path traversal attempts
  filename = filename.replace(/\.\./g, '')

  // Remove or replace dangerous characters
  filename = filename.replace(/[<>:"/\\|?*\x00-\x1f]/g, '_')

  // Limit length
  if (filename.length > 255) {
    const ext = filename.split('.').pop() || ''
    const nameWithoutExt = filename.substring(0, filename.lastIndexOf('.'))
    filename = nameWithoutExt.substring(0, 250 - ext.length) + '.' + ext
  }

  return filename
}

export function validateFileType(file: File): boolean {
  const hasValidType = ACCEPTED_FILE_TYPES.includes(file.type)
  const hasValidExtension = ACCEPTED_FILE_EXTENSIONS.some((ext) =>
    file.name.toLowerCase().endsWith(ext)
  )
  return hasValidType || hasValidExtension
}

export function validateFileSize(file: File): boolean {
  return file.size <= MAX_FILE_SIZE
}

export const FILE_VALIDATION = {
  MAX_FILE_SIZE,
  ACCEPTED_FILE_TYPES,
  ACCEPTED_FILE_EXTENSIONS,
} as const
