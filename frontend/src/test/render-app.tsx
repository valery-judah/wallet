import { QueryClientProvider } from "@tanstack/react-query"
import { RouterProvider } from "@tanstack/react-router"
import { render } from "@testing-library/react"
import { ThemeProvider } from "@/components/theme-provider"
import { createAppQueryClient } from "@/lib/query-client"
import { createAppRouter } from "@/router"

export function renderApp(initialPath: string) {
  window.history.pushState({}, "", initialPath)

  const queryClient = createAppQueryClient()
  const router = createAppRouter()

  return {
    queryClient,
    router,
    ...render(
      <ThemeProvider defaultTheme="light" storageKey="wallet-ui-theme-test">
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </ThemeProvider>,
    ),
  }
}
