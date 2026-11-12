import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchListings } from './search'
import type { SearchQuery, SearchState } from './types'

export function useListings(query: SearchQuery) {
  const queryClient = useQueryClient()
  const result = useQuery({
    queryKey: ['listings', query],
    queryFn: ({ signal }) => fetchListings(query, signal),
  })

  let state: SearchState
  if (result.isPending || result.isFetching) {
    state = { status: 'loading' }
  } else if (result.isError) {
    state = {
      status: 'error',
      message:
        result.error instanceof TypeError
          ? 'Could not reach the listing service. Check your connection and try again.'
          : result.error instanceof Error
            ? result.error.message
            : 'Something went wrong. Please try again.',
    }
  } else {
    state = { status: 'success', data: result.data }
  }

  return {
    state,
    retry: () => {
      void result.refetch()
    },
    // Explicit submissions must refresh even when their query key is unchanged.
    refresh: (nextQuery: SearchQuery) =>
      queryClient.invalidateQueries({
        queryKey: ['listings', nextQuery],
        exact: true,
      }),
  }
}
