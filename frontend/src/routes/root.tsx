import type { ReactNode } from "react"
import { Link } from "@tanstack/react-router"
import { Footer } from "@/components/Common/Footer"
import AppSidebar from "@/components/Sidebar/AppSidebar"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"

export function RootLayout({ children }: { children: ReactNode }) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-4 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <SidebarTrigger className="-ml-1 text-muted-foreground" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium">Wallet</p>
            <p className="truncate text-xs text-muted-foreground">
              Track where your money lives and how you spend it.
            </p>
          </div>
        </header>
        <main className="flex-1 p-6 md:p-8">
          <div className="mx-auto max-w-7xl">{children}</div>
        </main>
        <Footer />
      </SidebarInset>
    </SidebarProvider>
  )
}

export function NotFoundPage() {
  return (
    <section className="mx-auto max-w-2xl rounded-xl border bg-card p-10 text-center shadow-sm">
      <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">
        Not found
      </p>
      <h2 className="mt-4 text-3xl font-semibold">This page does not exist.</h2>
      <p className="mt-3 text-sm text-muted-foreground">
        Return to the main app and pick an existing section.
      </p>
      <Link
        className="mt-8 inline-flex rounded-md bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90"
        to="/accounts"
      >
        Back to app
      </Link>
    </section>
  )
}

export function ErrorPage() {
  return (
    <section className="mx-auto max-w-2xl rounded-xl border bg-card p-10 text-center shadow-sm">
      <p className="text-xs uppercase tracking-[0.28em] text-destructive">
        Unexpected error
      </p>
      <h2 className="mt-4 text-3xl font-semibold">
        Something went wrong while loading the wallet UI.
      </h2>
      <p className="mt-3 text-sm text-muted-foreground">
        Refresh the page or return to the main app.
      </p>
      <Link
        className="mt-8 inline-flex rounded-md border bg-background px-5 py-3 text-sm font-semibold transition hover:bg-accent"
        to="/accounts"
      >
        Return to app
      </Link>
    </section>
  )
}
