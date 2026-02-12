'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useUploadDocument } from '@/lib/hooks/useDocuments'
import { documentUploadSchema, sanitizeFilename } from '@/lib/validation/document'
import type { DocumentUploadInput } from '@/lib/validation/document'

interface UploadFormClientProps {
  acceptedExtensions: string
}

export function UploadFormClient({ acceptedExtensions }: UploadFormClientProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
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

    // Validate before upload
    const validation = documentUploadSchema.safeParse({
      file,
      domain: data.domain,
      description: data.description,
    })
    if (!validation.success) {
      return
    }

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
      onSuccess: () => {
        reset()
        setSelectedFile(null)
      },
    })
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    setSelectedFile(file || null)
  }

  return (
    <>
      <input
        id="file"
        type="file"
        accept={acceptedExtensions}
        {...register('file', {
          required: 'File is required',
          onChange: handleFileChange,
        })}
        className="block w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/90"
      />
      {formErrors.file && (
        <p className="text-sm text-red-600 mt-1">{formErrors.file.message?.toString()}</p>
      )}

      {selectedFile && (
        <div className="text-sm space-y-1 mt-4">
          <p>
            <span className="font-medium">Selected:</span> {selectedFile.name}
          </p>
          <p>
            <span className="font-medium">Size:</span>{' '}
            {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
          </p>
        </div>
      )}

      <input
        id="domain"
        type="text"
        {...register('domain')}
        placeholder="e.g., science, law, medical"
        className="block w-full px-3 py-2 border rounded-md text-sm"
      />

      <textarea
        id="description"
        {...register('description')}
        rows={3}
        placeholder="Brief description of the document"
        className="block w-full px-3 py-2 border rounded-md text-sm"
      />

      {uploadMutation.isError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">
          {uploadMutation.error.message}
        </div>
      )}

      {uploadMutation.isSuccess && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-md text-sm text-green-800">
          Document uploaded successfully! Processing will begin shortly.
        </div>
      )}

      <button
        type="submit"
        disabled={uploadMutation.isPending || !selectedFile}
        className="w-full py-2 px-4 bg-primary text-primary-foreground rounded-md font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90"
      >
        {uploadMutation.isPending ? 'Uploading...' : 'Upload Document'}
      </button>
    </>
  )
}
