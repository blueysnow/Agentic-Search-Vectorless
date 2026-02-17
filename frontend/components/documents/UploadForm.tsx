'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { useUploadDocument } from '@/lib/hooks/useDocuments'
import { documentUploadSchema, sanitizeFilename, FILE_VALIDATION } from '@/lib/validation/document'
import { toast } from '@/lib/hooks/use-toast'
import type { DocumentUploadInput } from '@/lib/validation/document'
import type { IngestResponse } from '@/lib/api/types'

export function UploadForm() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [lastUploadedDoc, setLastUploadedDoc] = useState<IngestResponse | null>(null)
  const uploadMutation = useUploadDocument()

  const {
    register,
    handleSubmit,
    formState: { errors: formErrors },
    reset,
  } = useForm<DocumentUploadInput>()

  const onSubmit = (data: DocumentUploadInput) => {
    const file = selectedFile || (data.file as unknown as File)
    if (!file) return

    // SF-009 Fix: Display validation errors to user
    const validation = documentUploadSchema.safeParse({
      file,
      domain: data.domain,
      description: data.description
    })
    if (!validation.success) {
      const errorMessage = validation.error.errors[0].message
      setValidationError(errorMessage)
      return
    }

    // Clear validation error on successful validation
    setValidationError(null)
    setLastUploadedDoc(null)

    const formData = new FormData()
    const sanitizedName = sanitizeFilename(file.name)

    // Create a new File with sanitized name
    const sanitizedFile = new File([file], sanitizedName, {
      type: file.type,
    })

    formData.append('file', sanitizedFile)
    if (data.domain) formData.append('domain', data.domain)
    if (data.description) formData.append('description', data.description)

    uploadMutation.mutate(formData, {
      onSuccess: (response) => {
        reset()
        setSelectedFile(null)
        setLastUploadedDoc(response)
        toast({
          title: 'Upload successful',
          description: `"${response.name}" has been uploaded and is being processed.`,
        })
      },
    })
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    setSelectedFile(file || null)
    // Clear previous upload result when selecting new file
    setLastUploadedDoc(null)
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 p-6 border rounded-lg">
      <div>
        <label htmlFor="file" className="block text-sm font-medium mb-2">
          Document File *
        </label>
        <input
          id="file"
          type="file"
          accept={FILE_VALIDATION.ACCEPTED_FILE_EXTENSIONS.join(',')}
          {...register('file', {
            required: 'File is required',
            onChange: handleFileChange,
          })}
          className="block w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/90 file:cursor-pointer"
        />
        {formErrors.file && (
          <p className="text-sm text-red-600 mt-1">{formErrors.file.message?.toString()}</p>
        )}
        <p className="text-xs text-muted-foreground mt-1">
          Accepted: PDF, Markdown, Text (.pdf, .md, .markdown, .txt) -- Max: 50MB
        </p>
      </div>

      {selectedFile && (
        <div className="text-sm space-y-1">
          <p>
            <span className="font-medium">Selected:</span> {selectedFile.name}
          </p>
          <p>
            <span className="font-medium">Size:</span>{' '}
            {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
          </p>
        </div>
      )}

      <div>
        <label htmlFor="domain" className="block text-sm font-medium mb-2">
          Domain (optional)
        </label>
        <input
          id="domain"
          type="text"
          {...register('domain')}
          placeholder="e.g., science, law, medical"
          className="block w-full px-3 py-2 border rounded-md text-sm"
        />
      </div>

      <div>
        <label htmlFor="description" className="block text-sm font-medium mb-2">
          Description (optional)
        </label>
        <textarea
          id="description"
          {...register('description')}
          rows={3}
          placeholder="Brief description of the document"
          className="block w-full px-3 py-2 border rounded-md text-sm"
        />
      </div>

      {validationError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">
          {validationError}
        </div>
      )}

      {uploadMutation.isError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">
          {uploadMutation.error.message}
        </div>
      )}

      {/* Upload progress bar */}
      {uploadMutation.isPending && uploadMutation.uploadProgress !== null && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-gray-600">
            {uploadMutation.uploadProgress >= 99 ? (
              <span>Processing document...</span>
            ) : (
              <span>Uploading...</span>
            )}
            <span>{uploadMutation.uploadProgress}%</span>
          </div>
          <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-600 rounded-full transition-all duration-300 ease-out"
              style={{ width: `${uploadMutation.uploadProgress}%` }}
            />
          </div>
          {uploadMutation.uploadProgress >= 99 && (
            <p className="text-xs text-gray-500">
              File received. Building document index with AI (this may take a minute)...
            </p>
          )}
        </div>
      )}

      {/* Success banner with chat link */}
      {lastUploadedDoc && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-md text-sm text-green-800">
          <p className="font-medium">Document uploaded and indexed successfully!</p>
          <p className="mt-1">Your document is ready to query.</p>
          <Link
            href={`/query?documentId=${lastUploadedDoc.documentId}`}
            className="inline-flex items-center mt-2 text-sm font-medium text-green-700 hover:text-green-900 cursor-pointer"
          >
            Chat about this document &rarr;
          </Link>
        </div>
      )}

      <button
        type="submit"
        disabled={uploadMutation.isPending || !selectedFile}
        className="w-full py-2 px-4 bg-primary text-primary-foreground rounded-md font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 cursor-pointer"
      >
        {uploadMutation.isPending
          ? uploadMutation.uploadProgress !== null && uploadMutation.uploadProgress >= 99
            ? 'Processing...'
            : 'Uploading...'
          : 'Upload Document'}
      </button>
    </form>
  )
}
