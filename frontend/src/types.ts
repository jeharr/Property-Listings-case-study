export interface Listing {
  id: string
  source: string
  address: string
  city: string
  state: string
  zip: string
  price: number
  bedrooms: number
  bathrooms: number
  sqft: number
  latitude: number
  longitude: number
  listedDate: string
  status: 'active' | 'pending' | 'sold'
  description: string
  relevanceScore: number
  budgetScore: number | null
  recencyScore: number
}

export interface SearchResponse {
  items: Listing[]
  total: number
  page: number
  pageSize: number
  totalPages: number
  scoringDate: string
}

export type SearchState =
  | { status: 'loading' }
  | { status: 'success'; data: SearchResponse }
  | { status: 'error'; message: string }

export interface SearchQuery {
  minPrice?: number
  maxPrice?: number
  minBedrooms?: number
  city?: string
  keyword?: string
  targetBudget?: number
  page: number
}

export const emptyForm = {
  minPrice: '',
  maxPrice: '',
  minBedrooms: '',
  city: '',
  keyword: '',
  targetBudget: '',
}
export type FilterForm = typeof emptyForm
export type FieldErrors = Partial<Record<keyof FilterForm, string>>
