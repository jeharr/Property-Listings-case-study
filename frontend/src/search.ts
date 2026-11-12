import type {
  FieldErrors,
  FilterForm,
  SearchQuery,
  SearchResponse,
} from './types'

export function validateFilters(form: FilterForm): {
  query: SearchQuery
  errors: FieldErrors
} {
  const errors: FieldErrors = {}
  const query: SearchQuery = { page: 1 }
  for (const field of [
    'minPrice',
    'maxPrice',
    'minBedrooms',
    'targetBudget',
  ] as const) {
    const raw = form[field].trim()
    if (!raw) continue
    const value = Number(raw)
    if (!Number.isFinite(value) || !/^\d+(\.\d+)?$/.test(raw)) {
      errors[field] = 'Enter a valid, non-negative number.'
    } else if (field === 'targetBudget' && value <= 0) {
      errors[field] = 'Target budget must be greater than zero.'
    } else if (field === 'minBedrooms' && !Number.isInteger(value)) {
      errors[field] = 'Bedrooms must be a whole number.'
    } else {
      query[field] = value
    }
  }
  if (
    query.minPrice !== undefined &&
    query.maxPrice !== undefined &&
    query.minPrice > query.maxPrice
  ) {
    errors.maxPrice = 'Maximum price must be at least the minimum price.'
  }
  if (form.city.trim()) query.city = form.city.trim()
  if (form.keyword.trim()) query.keyword = form.keyword.trim()
  return { query, errors }
}

export async function fetchListings(
  query: SearchQuery,
  signal: AbortSignal,
): Promise<SearchResponse> {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined) params.set(key, String(value))
  }
  const response = await fetch(`/api/listings?${params}`, { signal })
  if (!response.ok) {
    if (response.status === 422) {
      const body = (await response.json()) as { detail?: { msg: string }[] }
      const details = Array.isArray(body.detail)
        ? body.detail.map((item) => item.msg).join(' ')
        : ''
      throw new Error(
        details || 'Please check your search filters and page number.',
      )
    }
    throw new Error('The listing service is unavailable. Please try again.')
  }
  return response.json() as Promise<SearchResponse>
}
