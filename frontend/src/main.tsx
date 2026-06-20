import { QueryClientProvider } from "@tanstack/react-query"
import { RouterProvider } from "@tanstack/react-router"
import { StrictMode } from "react"
import ReactDOM from "react-dom/client"
import { ThemeProvider } from "@/components/theme-provider"
import { configureClient } from "@/configure-client"
import "@/index.css"
import { createAppQueryClient } from "@/lib/query-client"
import { appRouter } from "@/router"

configureClient()
const queryClient = createAppQueryClient()

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="light" storageKey="wallet-ui-theme">
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={appRouter} />
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
)
