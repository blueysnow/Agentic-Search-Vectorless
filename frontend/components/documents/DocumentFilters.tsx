'use client'

import { useCallback } from 'react'
import type { DocumentFilters as Filters } from '@/lib/api/types'

interface DocumentFiltersProps {
  filters: Filters
  onChange: (filters: Filters | ((prev: Filters) => Filters)) => void
}

export function DocumentFilters({ filters, onChange }: DocumentFiltersProps) {
  // Pattern 5.7: Functional setState for stable callbacks
  const handleStatusChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const value = e.target.value
      onChange((prev) => ({
        ...prev,
        status: value ? (value as Filters['status']) : undefined,
      }))
    },
    [onChange]
  )

  const handleDomainChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange((prev) => ({
        ...prev,
        domain: e.target.value || undefined,
      }))
    },
    [onChange]
  )

  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange((prev) => ({
        ...prev,
        q: e.target.value || undefined,
      }))
    },
    [onChange]
  )

  const handleClearFilters = useCallback(() => {
    onChange({})
  }, [onChange])

  return (
    <div className="space-y-4 p-4 border rounded-lg bg-gray-50">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">Filters</h3>
        <button
          onClick={handleClearFilters}
          className="text-sm text-blue-600 hover:underline"
        >
          Clear all
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label htmlFor="status-filter" className="block text-sm font-medium mb-1">
            Status
          </label>
          <select
            id="status-filter"
            value={filters.status || ''}
            onChange={handleStatusChange}
            className="w-full px-3 py-2 border rounded-md text-sm"
          >
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
        </div>

        <div>
          <label htmlFor="domain-filter" className="block text-sm font-medium mb-1">
            Domain
          </label>
          <input
            id="domain-filter"
            type="text"
            value={filters.domain || ''}
            onChange={handleDomainChange}
            placeholder="e.g., science, law"
            className="w-full px-3 py-2 border rounded-md text-sm"
          />
        </div>

        <div>
          <label htmlFor="search-filter" className="block text-sm font-medium mb-1">
            Search
          </label>
          <input
            id="search-filter"
            type="text"
            value={filters.q || ''}
            onChange={handleSearchChange}
            placeholder="Search documents..."
            className="w-full px-3 py-2 border rounded-md text-sm"
          />
        </div>
      </div>
    </div>
  )
}
