import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { AccountPageIntro, AccountSectionStack } from "@/components/accounts/account-layout"
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
    <AccountSectionStack className="gap-6">
      <AccountPageIntro
        action={
          <Button asChild className="h-10 rounded-full px-5 text-sm font-semibold">
            <Link to="/accounts/new">New account</Link>
          </Button>
        }
        description="Review your accounts across cards, cash, banks, and wallets, then open one or set up a new account."
        eyebrow="Accounts"
        title="See every account, grouped by type and balance."
      />
      <AccountList accounts={accounts} />
    </AccountSectionStack>
  )
}
