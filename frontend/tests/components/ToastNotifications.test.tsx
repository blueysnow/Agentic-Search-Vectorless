import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { toast } from '@/lib/hooks/use-toast'
import { Toaster } from '@/components/ui/toaster'

describe('Toast Notifications', () => {
  it('displays success toast with title and description', async () => {
    render(<Toaster />)

    toast({
      title: 'Upload successful',
      description: 'Your document is being processed.',
    })

    await waitFor(() => {
      expect(screen.getByText('Upload successful')).toBeInTheDocument()
      expect(screen.getByText('Your document is being processed.')).toBeInTheDocument()
    })
  })

  it('displays error toast with destructive variant', async () => {
    render(<Toaster />)

    toast({
      variant: 'destructive',
      title: 'Upload failed',
      description: 'Could not upload document.',
    })

    await waitFor(() => {
      expect(screen.getByText('Upload failed')).toBeInTheDocument()
      expect(screen.getByText('Could not upload document.')).toBeInTheDocument()
    })
  })
})
