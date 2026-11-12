import { describe, expect, it, vi } from 'vitest'
import { fetchListings, validateFilters } from './search'
import { emptyForm } from './types'

describe('filter validation', () => {
  it('omits blank optional values and preserves zero', () => {
    expect(
      validateFilters({
        ...emptyForm,
        minPrice: '0',
        minBedrooms: '0',
        city: '  ',
        keyword: '  ',
      }),
    ).toEqual({ query: { minPrice: 0, minBedrooms: 0, page: 1 }, errors: {} })
  })
  it('trims text and numeric fields', () => {
    expect(
      validateFilters({
        ...emptyForm,
        targetBudget: ' 450000 ',
        city: ' Reston ',
        keyword: ' pool ',
      }).query,
    ).toEqual({
      targetBudget: 450000,
      city: 'Reston',
      keyword: 'pool',
      page: 1,
    })
  })
  it.each(['-1', 'NaN', 'Infinity', '450k', '1,000', '0x10'])(
    'rejects invalid price %s',
    (minPrice) => {
      expect(
        validateFilters({ ...emptyForm, minPrice }).errors.minPrice,
      ).toBeTruthy()
    },
  )
  it('rejects fractional bedrooms, zero budget, and inverted prices', () => {
    const { errors } = validateFilters({
      ...emptyForm,
      minBedrooms: '1.5',
      targetBudget: '0',
      minPrice: '500',
      maxPrice: '400',
    })
    expect(Object.keys(errors).sort()).toEqual([
      'maxPrice',
      'minBedrooms',
      'targetBudget',
    ])
  })
  it('accepts equal price bounds', () => {
    expect(
      validateFilters({ ...emptyForm, minPrice: '500', maxPrice: '500' })
        .errors,
    ).toEqual({})
  })
})

describe('API client', () => {
  it('encodes all filters and passes the cancellation signal', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ items: [] })))
    vi.stubGlobal('fetch', fetch)
    const signal = new AbortController().signal
    await fetchListings(
      {
        page: 2,
        minPrice: 0,
        maxPrice: 600000,
        minBedrooms: 3,
        city: 'Falls Church',
        keyword: 'yard & pool',
        targetBudget: 500000,
      },
      signal,
    )
    const [url, options] = fetch.mock.calls[0]
    const params = new URL(url, 'http://localhost').searchParams
    expect(Object.fromEntries(params)).toEqual({
      page: '2',
      minPrice: '0',
      maxPrice: '600000',
      minBedrooms: '3',
      city: 'Falls Church',
      keyword: 'yard & pool',
      targetBudget: '500000',
    })
    expect(options.signal).toBe(signal)
  })
  it('surfaces API validation errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: [{ msg: 'Page must be between 1 and 2.' }],
          }),
          { status: 422 },
        ),
      ),
    )
    await expect(
      fetchListings({ page: 3 }, new AbortController().signal),
    ).rejects.toThrow('Page must be between 1 and 2.')
  })
})
