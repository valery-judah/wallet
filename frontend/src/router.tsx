import {
  createRootRoute,
  createRoute,
  createRouter,
  HeadContent,
  Outlet,
  useNavigate,
} from "@tanstack/react-router"
import { useEffect } from "react"
import { AccountDetailRoute } from "@/routes/account-detail"
import { AccountsListRoute } from "@/routes/accounts-list"
import { AccountsNewRoute } from "@/routes/accounts-new"
import { CategoriesRoute } from "@/routes/categories"
import { ErrorPage, NotFoundPage, RootLayout } from "@/routes/root"

function HomeRedirect() {
  const navigate = useNavigate()

  useEffect(() => {
    void navigate({ replace: true, to: "/accounts" })
  }, [navigate])

  return null
}

const rootRoute = createRootRoute({
  component: () => (
    <>
      <HeadContent />
      <RootLayout>
        <Outlet />
      </RootLayout>
    </>
  ),
  errorComponent: ErrorPage,
  notFoundComponent: NotFoundPage,
})

const homeRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: HomeRedirect,
})

const accountsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "accounts",
  component: AccountsListRoute,
})

const accountsNewRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "accounts/new",
  component: AccountsNewRoute,
})

const accountDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "accounts/$accountId",
  component: AccountDetailRoute,
})

const categoriesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "categories",
  component: CategoriesRoute,
})

const routeTree = rootRoute.addChildren([
  homeRoute,
  accountsRoute,
  accountsNewRoute,
  accountDetailRoute,
  categoriesRoute,
])

export function createAppRouter() {
  return createRouter({ routeTree })
}

export const appRouter = createAppRouter()

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof appRouter
  }
}
