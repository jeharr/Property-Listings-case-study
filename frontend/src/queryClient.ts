import { QueryClient } from '@tanstack/react-query'

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: false,
        refetchOnWindowFocus: false,
        // Let fetch report offline errors rather than silently pausing the search.
        networkMode: 'always',
      },
    },
  })
}
