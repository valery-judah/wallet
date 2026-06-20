import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query"

function handleGlobalError(error: unknown): void {
  if (error instanceof Error) {
    console.error("Unexpected API error", error)
  }
}

export function createAppQueryClient(): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: handleGlobalError,
    }),
    mutationCache: new MutationCache({
      onError: handleGlobalError,
    }),
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })
}
