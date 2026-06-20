import {
  createRootRoute,
  createRoute,
  createRouter,
  HeadContent,
  Outlet,
  useNavigate,
} from "@tanstack/react-router"
import { useEffect } from "react"
import { CardDetailRoute } from "@/routes/card-detail"
import { CardsListRoute } from "@/routes/cards-list"
import { CardsNewRoute } from "@/routes/cards-new"
import { ErrorPage, NotFoundPage, RootLayout } from "@/routes/root"

function HomeRedirect() {
  const navigate = useNavigate()

  useEffect(() => {
    void navigate({ replace: true, to: "/cards" })
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

const cardsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "cards",
  component: CardsListRoute,
})

const cardsNewRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "cards/new",
  component: CardsNewRoute,
})

const cardDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "cards/$cardId",
  component: CardDetailRoute,
})

const routeTree = rootRoute.addChildren([
  homeRoute,
  cardsRoute,
  cardsNewRoute,
  cardDetailRoute,
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
