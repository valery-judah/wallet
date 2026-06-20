import { Link } from "@tanstack/react-router"
import type { AccountResponse } from "@/client"
import {
  ACCOUNT_TYPE_OPTIONS,
  AccountIcon,
  getAccountColorTheme,
  getAccountTypeLabel,
} from "@/components/accounts/account-appearance"
import { AccountSectionStack } from "@/components/accounts/account-layout"
import { formatDate, formatMoney } from "@/lib/format"
import { cn } from "@/lib/utils"

type AccountListProps = {
  accounts: Array<AccountResponse>
}

function formatCount(count: number, singular: string, plural: string) {
  return `${count} ${count === 1 ? singular : plural}`
}

function sumBalancesByCurrency(accounts: Array<AccountResponse>) {
  const totals = new Map<string, number>()

  accounts.forEach((account) => {
    const currency = account.current_balance.currency
    totals.set(
      currency,
      (totals.get(currency) ?? 0) + account.current_balance.amount_minor,
    )
  })

  return Array.from(totals.entries())
    .map(([currency, amountMinor]) => ({ amountMinor, currency }))
    .sort((left, right) => left.currency.localeCompare(right.currency))
}

function formatCurrencySummary(accounts: Array<AccountResponse>) {
  return sumBalancesByCurrency(accounts)
    .map((entry) => formatMoney(entry.amountMinor, entry.currency))
    .join(" · ")
}

function groupAccounts(accounts: Array<AccountResponse>) {
  return ACCOUNT_TYPE_OPTIONS.map((option) => ({
    accounts: accounts
      .filter((account) => account.type === option.value)
      .sort((left, right) => left.name.localeCompare(right.name)),
    description: option.description,
    type: option.value,
  })).filter((group) => group.accounts.length > 0)
}

export function AccountList({ accounts }: AccountListProps) {
  if (accounts.length === 0) {
    return (
      <section className="surface rounded-[2rem] p-8 text-center">
        <p className="text-lg font-semibold">No accounts yet.</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Create your first account to start tracking where your money lives.
        </p>
        <Link
          className="mt-6 inline-flex rounded-full bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90"
          to="/accounts/new"
        >
          Create an account
        </Link>
      </section>
    )
  }

  const activeAccounts = accounts.filter((account) => account.status === "active")
  const closedAccounts = accounts.filter((account) => account.status === "closed")
  const groupedAccounts = groupAccounts(accounts)

  return (
    <AccountSectionStack className="gap-6">
      <section className="grid gap-3 lg:grid-cols-3">
        <article className="rounded-[1.75rem] border border-border/70 bg-card/80 px-5 py-4">
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
            Tracked balance
          </p>
          <p className="mt-3 text-[1.65rem] font-semibold tracking-[-0.03em]">
            {formatCurrencySummary(accounts)}
          </p>
          <p className="mt-1.5 text-sm leading-5 text-muted-foreground">
            Totals stay separated by currency so each account keeps one clear balance.
          </p>
        </article>
        <article className="rounded-[1.75rem] border border-border/70 bg-card/80 px-5 py-4">
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
            Lifecycle
          </p>
          <p className="mt-3 text-[1.65rem] font-semibold tracking-[-0.03em]">
            {activeAccounts.length} active · {closedAccounts.length} closed
          </p>
          <p className="mt-1.5 text-sm leading-5 text-muted-foreground">
            Closed accounts remain visible for history and reporting.
          </p>
        </article>
        <article className="rounded-[1.75rem] border border-border/70 bg-card/80 px-5 py-4">
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
            Coverage
          </p>
          <p className="mt-3 text-[1.65rem] font-semibold tracking-[-0.03em]">
            {formatCount(accounts.length, "account", "accounts")} ·{" "}
            {formatCount(groupedAccounts.length, "type", "types")} in use
          </p>
          <p className="mt-1.5 text-sm leading-5 text-muted-foreground">
            Cards, cash, banks, and wallets can all be tracked here.
          </p>
        </article>
      </section>

      <AccountSectionStack className="gap-6">
        {groupedAccounts.map((group) => (
          <div className="grid gap-4" key={group.type}>
            <header className="grid gap-2.5 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
              <div>
                <p className="text-[0.68rem] uppercase tracking-[0.22em] text-muted-foreground">
                  {formatCount(group.accounts.length, "account", "accounts")}
                </p>
                <h3 className="mt-1.5 text-[1.75rem] font-semibold tracking-[-0.03em]">
                  {getAccountTypeLabel(group.type)}
                </h3>
                <p className="mt-1.5 max-w-2xl text-sm leading-5 text-muted-foreground">
                  {group.description}
                </p>
              </div>
              <p className="inline-flex rounded-full border border-border/70 bg-card/50 px-3.5 py-1.5 text-xs font-medium text-muted-foreground md:justify-self-end">
                {formatCurrencySummary(group.accounts)}
              </p>
            </header>

            <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
              {group.accounts.map((account) => {
                const theme = getAccountColorTheme(account.type, account.color_key)

                return (
                  <Link
                    className={cn(
                      "group relative block overflow-hidden rounded-[1.75rem] border bg-card/80 px-5 py-4 shadow-[0_18px_60px_-42px_rgba(15,23,42,0.5)] transition hover:border-border hover:bg-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                      theme.borderClassName,
                    )}
                    key={account.id}
                    params={{ accountId: account.id }}
                    to="/accounts/$accountId"
                  >
                    <div
                      className={cn(
                        "absolute inset-x-0 top-0 h-[5.75rem] bg-gradient-to-r",
                        theme.previewGlowClassName,
                      )}
                    />
                    <div className="absolute inset-x-0 top-[5.75rem] h-px bg-border/40" />
                    <div className="absolute inset-x-0 bottom-0 h-28 bg-gradient-to-t from-card via-card/94 to-transparent" />
                    <div className="relative flex h-full min-h-[14.5rem] flex-col">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex min-w-0 items-start gap-3">
                          <div
                            className={cn(
                              "flex size-11 shrink-0 items-center justify-center rounded-[1.35rem]",
                              theme.iconWrapClassName,
                            )}
                          >
                            <AccountIcon type={account.type} />
                          </div>
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <span
                                className={cn(
                                  "rounded-full px-2.5 py-1 text-[0.72rem] font-semibold",
                                  theme.badgeClassName,
                                )}
                              >
                                {getAccountTypeLabel(account.type)}
                              </span>
                              <span className="text-[0.72rem] uppercase tracking-[0.18em] text-muted-foreground">
                                {account.currency}
                              </span>
                            </div>
                            <h2 className="mt-2 truncate text-[1.85rem] leading-none font-semibold tracking-[-0.03em]">
                              {account.name}
                            </h2>
                          </div>
                        </div>
                        <span
                          className={cn(
                            "rounded-full px-2.5 py-1 text-[0.72rem] font-semibold",
                            account.status === "closed"
                              ? "bg-slate-500/12 text-slate-200"
                              : theme.badgeClassName,
                          )}
                        >
                          {account.status}
                        </span>
                      </div>

                      <div className="mt-auto pt-7">
                        <p className="text-[2rem] leading-none font-semibold tracking-[-0.04em]">
                          {formatMoney(
                            account.current_balance.amount_minor,
                            account.current_balance.currency,
                          )}
                        </p>
                        <div className="mt-5 flex items-end justify-between gap-3">
                          <p className="text-sm text-muted-foreground">
                          {account.status === "closed" && account.closed_on
                            ? `Closed ${formatDate(account.closed_on)}`
                            : `Opened ${formatDate(account.opened_on)}`}
                          </p>

                          <span className="inline-flex rounded-full border border-border/80 px-3.5 py-1.5 text-sm font-semibold text-foreground transition group-hover:bg-accent">
                            Open account
                          </span>
                        </div>
                      </div>
                    </div>
                  </Link>
                )
              })}
            </div>
          </div>
        ))}
      </AccountSectionStack>
    </AccountSectionStack>
  )
}
