import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { createQueryClient } from './queryClient'
import type { Listing, SearchResponse } from './types'

const clients: ReturnType<typeof createQueryClient>[] = []

function renderApp() {
  const client = createQueryClient()
  clients.push(client)
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  )
}

afterEach(() => {
  clients.forEach((client) => client.clear())
  clients.length = 0
})

const listing: Listing = {
  id: 'A1',
  source: 'MLS_A',
  address: '123 Main St',
  city: 'Springfield',
  state: 'VA',
  zip: '22150',
  price: 450000,
  bedrooms: 2,
  bathrooms: 1.5,
  sqft: 980,
  latitude: 38,
  longitude: -77,
  listedDate: '2026-08-29',
  status: 'active',
  description: 'Bright condo near shops.',
  relevanceScore: 87.42,
  budgetScore: 100,
  recencyScore: 58.06,
}
const payload = (overrides: Partial<SearchResponse> = {}): SearchResponse => ({
  items: [listing],
  page: 1,
  pageSize: 6,
  totalPages: 2,
  total: 12,
  scoringDate: '2026-11-10',
  ...overrides,
})
const response = (overrides: Partial<SearchResponse> = {}) =>
  new Response(JSON.stringify(payload(overrides)))

describe('listing search', () => {
  it('delays loading for one second, then shows listing details and fixed pagination', async () => {
    vi.useFakeTimers()
    try {
      let resolveSearch!: (value: Response) => void
      vi.stubGlobal(
        'fetch',
        vi.fn().mockImplementation(
          () =>
            new Promise<Response>((resolve) => {
              resolveSearch = resolve
            }),
        ),
      )
      renderApp()
      expect(screen.queryByText('Searching listings…')).not.toBeInTheDocument()
      await act(async () => {
        await vi.advanceTimersByTimeAsync(999)
      })
      expect(screen.queryByText('Searching listings…')).not.toBeInTheDocument()
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1)
      })
      expect(screen.getByText('Searching listings…')).toBeInTheDocument()
      await act(async () => {
        resolveSearch(response())
        await vi.advanceTimersByTimeAsync(0)
      })
      expect(screen.queryByText('Searching listings…')).not.toBeInTheDocument()
      expect(
        screen.getByRole('row', { name: '123 Main St' }),
      ).toBeInTheDocument()
      expect(screen.getByText('$450,000')).toBeInTheDocument()
      expect(screen.getByText('87.42')).toBeInTheDocument()
      expect(screen.getByText('6 per page')).toBeInTheDocument()
      expect(
        screen.getByRole('button', { name: 'Previous page' }),
      ).toBeDisabled()
    } finally {
      vi.useRealTimers()
    }
  })

  it('prevents invalid searches, focuses the invalid field, and shows inline errors', async () => {
    const user = userEvent.setup()
    const fetch = vi.fn().mockResolvedValue(response())
    vi.stubGlobal('fetch', fetch)
    renderApp()
    await screen.findByRole('table', { name: 'Listing results' })
    await user.type(screen.getByLabelText('Min. price'), '500000')
    await user.type(screen.getByLabelText('Max. price'), '400000')
    await user.click(screen.getByRole('button', { name: 'Search listings' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Please check')
    expect(screen.getByLabelText('Max. price')).toHaveFocus()
    expect(screen.getByLabelText('Max. price')).toHaveAttribute(
      'aria-invalid',
      'true',
    )
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('keeps applied filters across pages and resets the page when searching', async () => {
    const user = userEvent.setup()
    const restonListings = Array.from({ length: 4 }, (_, index) => ({
      ...listing,
      id: `R${index + 1}`,
      address: `${index + 1} Reston Test St`,
      city: 'Reston',
    }))
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(response())
      .mockResolvedValueOnce(
        response({
          items: restonListings.slice(0, 3),
          pageSize: 3,
          total: 4,
          totalPages: 2,
        }),
      )
      .mockResolvedValueOnce(
        response({
          items: restonListings.slice(3),
          page: 2,
          pageSize: 3,
          total: 4,
          totalPages: 2,
        }),
      )
      .mockResolvedValueOnce(response({ pageSize: 3, total: 1, totalPages: 1 }))
    const requestParams = (index: number) =>
      Object.fromEntries(
        new URL(fetch.mock.calls[index][0], 'http://localhost').searchParams,
      )
    vi.stubGlobal('fetch', fetch)
    renderApp()
    await screen.findByRole('table', { name: 'Listing results' })
    await user.type(screen.getByLabelText('City'), 'Reston')
    await user.type(screen.getByLabelText('Target budget'), '500000')
    await user.click(screen.getByRole('button', { name: 'Search listings' }))
    await screen.findByText('4 listings')
    expect(requestParams(1)).toEqual({
      city: 'Reston',
      targetBudget: '500000',
      page: '1',
    })

    await user.click(screen.getByRole('button', { name: 'Next page' }))
    await screen.findByText('Showing 4–4 of 4')
    expect(
      screen.getByRole('row', { name: '4 Reston Test St' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next page' })).toBeDisabled()
    expect(requestParams(2)).toEqual({
      city: 'Reston',
      targetBudget: '500000',
      page: '2',
    })

    await user.clear(screen.getByLabelText('City'))
    await user.type(screen.getByLabelText('City'), 'Springfield')
    await user.click(screen.getByRole('button', { name: 'Search listings' }))
    await screen.findByText('1 listing')
    expect(requestParams(3)).toEqual({
      city: 'Springfield',
      targetBudget: '500000',
      page: '1',
    })
    expect(
      screen.getByRole('button', { name: 'Go to page 1' }),
    ).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('button', { name: 'Previous page' })).toBeDisabled()
  })

  it('reuses fresh cached pages when navigating back', async () => {
    const user = userEvent.setup()
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(response())
      .mockResolvedValueOnce(response({ page: 2 }))
    vi.stubGlobal('fetch', fetch)
    renderApp()
    await screen.findByRole('table', { name: 'Listing results' })
    await user.click(screen.getByRole('button', { name: 'Next page' }))
    await screen.findByText('Showing 7–12 of 12')
    await user.click(screen.getByRole('button', { name: 'Previous page' }))
    await screen.findByText('Showing 1–6 of 12')
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('revalidates cached pages after the freshness window expires', async () => {
    let now = Date.now()
    vi.spyOn(Date, 'now').mockImplementation(() => now)
    const user = userEvent.setup()
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(response())
      .mockResolvedValueOnce(response({ page: 2 }))
      .mockResolvedValueOnce(
        response({ items: [{ ...listing, price: 499000 }] }),
      )
    vi.stubGlobal('fetch', fetch)
    renderApp()
    await screen.findByRole('table', { name: 'Listing results' })
    await user.click(screen.getByRole('button', { name: 'Next page' }))
    await screen.findByText('Showing 7–12 of 12')
    now += 31_000
    await user.click(screen.getByRole('button', { name: 'Previous page' }))
    await screen.findByText('$499,000')
    expect(fetch).toHaveBeenCalledTimes(3)
  })

  it('refreshes an unchanged search instead of returning only cached data', async () => {
    const user = userEvent.setup()
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(response())
      .mockResolvedValueOnce(
        response({ items: [{ ...listing, price: 499000 }] }),
      )
    vi.stubGlobal('fetch', fetch)
    renderApp()
    await screen.findByText('$450,000')
    await user.click(screen.getByRole('button', { name: 'Search listings' }))
    await screen.findByText('$499,000')
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(fetch.mock.calls[0][0]).toBe(fetch.mock.calls[1][0])
  })

  it('refreshes the default query when resetting draft filters', async () => {
    const user = userEvent.setup()
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(response())
      .mockResolvedValueOnce(
        response({ items: [{ ...listing, price: 499000 }] }),
      )
    vi.stubGlobal('fetch', fetch)
    renderApp()
    await screen.findByText('$450,000')
    await user.type(screen.getByLabelText('City'), 'Reston')
    await user.click(screen.getByRole('button', { name: 'Reset filters' }))
    await screen.findByText('$499,000')
    expect(screen.getByLabelText('City')).toHaveValue('')
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(fetch.mock.calls[1][0]).toBe('/api/listings?page=1')
  })

  it('shows no results and can clear filters', async () => {
    const user = userEvent.setup()
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(response({ items: [], total: 0, totalPages: 0 }))
      .mockResolvedValueOnce(response())
    vi.stubGlobal('fetch', fetch)
    renderApp()
    expect(
      await screen.findByText('No listings match your search'),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('navigation', { name: 'Results pages' }),
    ).not.toBeInTheDocument()
    await user.type(screen.getByLabelText('City'), 'Atlantis')
    await user.click(screen.getByRole('button', { name: 'Clear filters' }))
    await screen.findByRole('table', { name: 'Listing results' })
    expect(screen.getByLabelText('City')).toHaveValue('')
    expect(fetch.mock.calls[1][0]).toBe('/api/listings?page=1')
  })

  it('shows a service error and retries the same search', async () => {
    const user = userEvent.setup()
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(new Response('', { status: 503 }))
      .mockResolvedValueOnce(response())
    vi.stubGlobal('fetch', fetch)
    renderApp()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The listing service is unavailable',
    )
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    await screen.findByRole('table', { name: 'Listing results' })
    expect(fetch.mock.calls[0][0]).toBe(fetch.mock.calls[1][0])
  })

  it('shows a clear network error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new TypeError('Failed to fetch')),
    )
    renderApp()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not reach the listing service',
    )
  })

  it('ignores stale responses after a newer search', async () => {
    const user = userEvent.setup()
    let resolveOld!: (value: Response) => void
    const fetch = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise<Response>((resolve) => {
            resolveOld = resolve
          }),
      )
      .mockResolvedValueOnce(response({ items: [], total: 0, totalPages: 0 }))
    vi.stubGlobal('fetch', fetch)
    renderApp()
    await user.type(screen.getByLabelText('City'), 'Atlantis')
    await user.click(screen.getByRole('button', { name: 'Search listings' }))
    await screen.findByText('No listings match your search')
    expect(fetch.mock.calls[0][1].signal.aborted).toBe(true)
    await act(async () => {
      resolveOld(response())
    })
    expect(
      screen.queryByRole('table', { name: 'Listing results' }),
    ).not.toBeInTheDocument()
  })
})
