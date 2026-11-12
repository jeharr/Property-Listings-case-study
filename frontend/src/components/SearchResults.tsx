import { useEffect, useState } from 'react'
import type { SearchState } from '../types'
import { ListingsTable } from './ListingsTable'
import { Pagination } from './Pagination'
import { EmptyState, ErrorState, LoadingState } from './SearchStates'

interface SearchResultsProps {
  state: SearchState
  hasTargetBudget: boolean
  onPageChange: (page: number) => void
  onRetry: () => void
  onReset: () => void
}

function DelayedLoadingState() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const timeout = window.setTimeout(() => setVisible(true), 1000)
    return () => window.clearTimeout(timeout)
  }, [])

  return visible ? <LoadingState /> : null
}

export function SearchResults({
  state,
  onPageChange,
  onRetry,
  onReset,
}: SearchResultsProps) {
  return (
    <section
      aria-labelledby="results-title"
      aria-busy={state.status === 'loading'}
    >
      <div className="results-heading">
        <h2 id="results-title">Results</h2>
        {state.status === 'success' && (
          <p role="status">
            {state.data.total} {state.data.total === 1 ? 'listing' : 'listings'}
          </p>
        )}
        <p className="muted">
          {state.status === 'success' && (
            <>
              {' '}
              · <span>{state.data.pageSize} per page</span>
            </>
          )}
        </p>
      </div>
      {state.status === 'loading' && <DelayedLoadingState />}
      {state.status === 'error' && (
        <ErrorState message={state.message} onRetry={onRetry} />
      )}
      {state.status === 'success' && (
        <>
          {state.data.total === 0 ? (
            <EmptyState onReset={onReset} />
          ) : (
            <>
              <ListingsTable listings={state.data.items} />
              <Pagination
                page={state.data.page}
                pageSize={state.data.pageSize}
                total={state.data.total}
                totalPages={state.data.totalPages}
                onPageChange={onPageChange}
              />
            </>
          )}
        </>
      )}
    </section>
  )
}
