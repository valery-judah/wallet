import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { AccountList } from "@/components/accounts/account-list"
import { Button } from "@/components/ui/button"
import { getApiErrorMessage } from "@/lib/api-errors"
import { accountsListOptions } from "@/lib/accounts"

export function AccountsListRoute() {
  const accountsQuery = useQuery(accountsListOptions())

  if (accountsQuery.isLoading) {
    return (
      <section className="surface rounded-[2rem] p-8">
        <p className="text-lg font-semibold">Loading accounts...</p>
      </section>
    )
  }

  if (accountsQuery.isError) {
    return (
      <section className="surface rounded-[2rem] p-8">
        <p className="text-lg font-semibold">Unable to load accounts.</p>
        <p className="mt-2 text-sm text-destructive">
          {getApiErrorMessage(accountsQuery.error)}
        </p>
      </section>
    )
  }

  const accounts = accountsQuery.data ?? []

  return (
    <div className="grid gap-8">
      <section className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">
            Accounts
          </p>
          <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">
            See every account and its current balance.
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Open an existing account or create a new one before money starts
            moving.
          </p>
        </div>
        <Button asChild>
          <Link to="/accounts/new">New account</Link>
        </Button>
      </section>

      <AccountList accounts={accounts} />
    </div>
  )
}
