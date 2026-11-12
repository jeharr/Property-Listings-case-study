import { useRef, useState } from 'react'
import type { SubmitEvent } from 'react'
import { AppHeader } from './components/AppHeader'
import { SearchFilters } from './components/SearchFilters'
import { SearchResults } from './components/SearchResults'
import { validateFilters } from './search'
import { emptyForm } from './types'
import type { FieldErrors, FilterForm, SearchQuery } from './types'
import { useListings } from './useListings'

export default function App() {
  const [form, setForm] = useState<FilterForm>({ ...emptyForm })
  const [errors, setErrors] = useState<FieldErrors>({})
  const [query, setQuery] = useState<SearchQuery>({ page: 1 })
  const formRef = useRef<HTMLFormElement>(null)
  const { state, retry, refresh } = useListings(query)

  function runSearch(nextQuery: SearchQuery) {
    setQuery(nextQuery)
    void refresh(nextQuery)
  }

  function onChange(name: keyof FilterForm, value: string) {
    setForm((current) => ({ ...current, [name]: value }))
    setErrors((current) => ({
      ...current,
      [name]: undefined,
      ...(name === 'minPrice' ? { maxPrice: undefined } : {}),
    }))
  }

  function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    const next = validateFilters(form)
    setErrors(next.errors)
    if (Object.keys(next.errors).length) {
      const first = Object.keys(next.errors)[0]
      formRef.current?.querySelector<HTMLInputElement>(`#${first}`)?.focus()
      return
    }
    runSearch(next.query)
  }

  function reset() {
    setForm({ ...emptyForm })
    setErrors({})
    runSearch({ page: 1 })
  }

  return (
    <main>
      <AppHeader />
      <div className="app-layout">
        <SearchFilters
          form={form}
          errors={errors}
          formRef={formRef}
          onChange={onChange}
          onSubmit={submit}
          onReset={reset}
        />
        <SearchResults
          state={state}
          hasTargetBudget={query.targetBudget !== undefined}
          onPageChange={(page) => setQuery((current) => ({ ...current, page }))}
          onRetry={retry}
          onReset={reset}
        />
      </div>
    </main>
  )
}
