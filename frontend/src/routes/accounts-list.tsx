import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { Plus } from "lucide-react"
import { AccountSectionStack } from "@/components/accounts/account-layout"
import { AccountList } from "@/components/accounts/account-list"
import { Button } from "@/components/ui/button"
import { getApiErrorMessage } from "@/lib/api-errors"
import { accountsListOptions } from "@/lib/accounts"
import { formatMoney } from "@/lib/format"

function formatAccountsBalanceSummary(
  accounts: Array<{
    current_balance: {
      amount_minor: number
      currency: string
    }
  }>,
) {
  const totals = new Map<string, number>()

  accounts.forEach((account) => {
    const currency = account.current_balance.currency
    totals.set(
      currency,
      (totals.get(currency) ?? 0) + account.current_balance.amount_minor,
    )
  })

  return Array.from(totals.entries())
    .sort(([leftCurrency], [rightCurrency]) => leftCurrency.localeCompare(rightCurrency))
    .map(([currency, amountMinor]) => formatMoney(amountMinor, currency))
    .join(" · ")
}

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
  const balanceSummary = formatAccountsBalanceSummary(accounts)

  return (
    <AccountSectionStack className="gap-8">
      <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
        <div>
          <h1 className="text-[2.55rem] leading-none font-black tracking-[-0.06em] text-foreground">
            Accounts
          </h1>
          <p className="mt-3 text-[1.05rem] text-muted-foreground">
            Total balance:{" "}
            <span className="font-bold text-foreground">
              {balanceSummary || "No balance yet"}
            </span>
          </p>
        </div>
        <Button
          asChild
          className="h-14 rounded-[1.35rem] px-6 text-base font-bold shadow-[0_14px_30px_-18px_rgba(239,190,58,0.7)]"
        >
          <Link to="/accounts/new">
            <Plus className="size-5" />
            Add Account
          </Link>
        </Button>
      </section>
      <AccountList accounts={accounts} />
    </AccountSectionStack>
  )
}
