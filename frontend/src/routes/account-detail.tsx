import { useQuery } from "@tanstack/react-query"
import { Link, useParams } from "@tanstack/react-router"
import type { ReactNode } from "react"
import {
  Clock3,
  Sparkles,
  TrendingDown,
  TrendingUp,
  X,
} from "lucide-react"
import type { TransactionResponse } from "@/client"
import {
  AccountIcon,
  type AccountTypeValue,
  getAccountColorTheme,
  getAccountTypeLabel,
} from "@/components/accounts/account-appearance"
import { getApiErrorMessage } from "@/lib/api-errors"
import { accountDetailOptions } from "@/lib/accounts"
import { formatDate, formatMoney } from "@/lib/format"
import { transactionsListOptions } from "@/lib/transactions"
import { cn } from "@/lib/utils"

type ActivitySnapshot = {
  incomeMinor: number
  expenseMinor: number
}

export function AccountDetailRoute() {
  const { accountId } = useParams({ from: "/accounts/$accountId" })
  const accountQuery = useQuery(accountDetailOptions(accountId))
  const transactionsQuery = useQuery(transactionsListOptions(accountId))

  if (accountQuery.isLoading) {
    return (
      <section className="rounded-xl border bg-card p-8 shadow-sm">
        <p className="text-lg font-semibold">Loading account...</p>
      </section>
    )
  }

  if (accountQuery.isError) {
    return (
      <section className="rounded-xl border bg-card p-8 shadow-sm">
        <p className="text-lg font-semibold">Unable to load this account.</p>
        <p className="mt-2 text-sm text-destructive">
          {getApiErrorMessage(accountQuery.error)}
        </p>
        <Link
          className="mt-6 inline-flex rounded-md border bg-background px-4 py-2 text-sm font-semibold transition hover:bg-accent"
          to="/accounts"
        >
          Back to accounts
        </Link>
      </section>
    )
  }

  const account = accountQuery.data
  const isArchived = account?.archived_at != null
  const theme = getAccountColorTheme(account?.type ?? "debit_card", account?.color_key)

  if (!account) {
    return (
      <section className="rounded-xl border bg-card p-8 shadow-sm">
        <p className="text-lg font-semibold">Account data is unavailable.</p>
      </section>
    )
  }

  const transactions = transactionsQuery.data ?? []
  const recentTransactions = sortRecentTransactions(transactions).slice(0, 5)
  const snapshot = summarizeAccountActivity(transactions, account.id)
  const latestActivity = recentTransactions[0]

  return (
    <section className="mx-auto w-full max-w-[1080px]">
      <div
        className={cn(
          "relative overflow-hidden rounded-[2.35rem] border border-white/8 bg-[linear-gradient(180deg,rgba(255,255,255,0.03),rgba(255,255,255,0.015))] px-6 py-6 shadow-[0_32px_80px_-42px_rgba(0,0,0,0.92)] sm:px-8 sm:py-8",
          theme.borderClassName,
        )}
      >
        <div
          className={cn(
            "absolute inset-x-0 top-0 h-[0.6rem] bg-gradient-to-r",
            theme.previewGlowClassName,
          )}
        />
        <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-black/10 to-transparent" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.05),transparent_38%)]" />
        <div className="relative">
          <div className="flex justify-end">
            <Link
              aria-label="Back to accounts"
              className="inline-flex size-12 items-center justify-center rounded-full border border-white/8 bg-background/70 text-muted-foreground transition hover:text-foreground"
              to="/accounts"
            >
              <X className="size-5" />
            </Link>
          </div>

          <div className="mt-4 grid gap-8 lg:grid-cols-[minmax(0,1fr)_240px] lg:items-start">
            <div className="min-w-0">
              <div className="flex items-start gap-4 sm:gap-5">
                <div
                  className={cn(
                    "flex size-20 shrink-0 items-center justify-center rounded-[1.7rem] shadow-[0_18px_40px_-24px_rgba(0,0,0,0.95)] sm:size-24",
                    theme.iconWrapClassName,
                  )}
                >
                  <AccountIcon type={account.type} className="size-9 sm:size-10" />
                </div>
                <div className="min-w-0 pt-1">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span
                      className={cn(
                        "rounded-full px-3 py-1 text-[0.95rem] font-semibold",
                        theme.badgeClassName,
                      )}
                    >
                      {getAccountTypeLabel(account.type)}
                    </span>
                    <span className="rounded-full border border-amber-500/30 bg-amber-500/8 px-3 py-1 text-[0.95rem] font-semibold text-amber-300">
                      {account.currency}
                    </span>
                    <span className="rounded-full border border-white/8 bg-white/5 px-3 py-1 text-[0.85rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                      {isArchived ? "Archived" : "Active"}
                    </span>
                  </div>
                  <h1 className="mt-5 truncate text-[3rem] leading-none font-black tracking-[-0.07em] text-foreground sm:text-[3.35rem]">
                    {account.name}
                  </h1>
                  <p className="mt-4 max-w-3xl text-[1.1rem] leading-8 text-muted-foreground">
                    {getAccountSummaryDescription(account.type, isArchived)}
                  </p>
                  <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 text-[0.95rem] text-muted-foreground">
                    <span>Opened {formatDate(account.opened_on)}</span>
                    {account.archived_at ? (
                      <span>Archived {formatDate(account.archived_at)}</span>
                    ) : null}
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-[1.7rem] border border-white/8 bg-background/82 px-5 py-4 shadow-[0_24px_40px_-30px_rgba(0,0,0,0.95)]">
              <p className="text-[0.78rem] font-bold uppercase tracking-[0.32em] text-muted-foreground">
                Current balance
              </p>
              <p className="mt-3 text-[2.5rem] leading-none font-black tracking-[-0.06em] text-foreground">
                {formatMoney(
                  account.current_balance.amount_minor,
                  account.current_balance.currency,
                )}
              </p>
            </div>
          </div>

          <div className="mt-8 grid gap-5 lg:grid-cols-[minmax(0,1.28fr)_minmax(280px,0.92fr)]">
            <div className="rounded-[2rem] border border-white/7 bg-background/72 p-6 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-[0.82rem] font-bold uppercase tracking-[0.32em] text-muted-foreground">
                    Flow snapshot
                  </p>
                  <p className="mt-3 text-[1.2rem] font-bold text-foreground">
                    Income vs expense movement
                  </p>
                </div>
                <Sparkles className="mt-0.5 size-5 text-amber-300" />
              </div>
              <div className="mt-7 h-4 rounded-full bg-white/5 p-0.5">
                <div
                  className={cn(
                    "h-full rounded-full bg-gradient-to-r",
                    snapshot.incomeMinor > 0 || snapshot.expenseMinor > 0
                      ? "from-rose-500 via-rose-400 to-orange-400"
                      : "from-white/8 via-white/6 to-white/4",
                  )}
                />
              </div>
              <div className="mt-7 grid gap-4 sm:grid-cols-2">
                <SnapshotMetricCard
                  accentClassName="border-emerald-500/25 text-emerald-400"
                  icon={<TrendingUp className="size-4 stroke-[2.1]" />}
                  label="Income"
                  value={formatSignedSnapshotValue(snapshot.incomeMinor, account.currency, "+")}
                />
                <SnapshotMetricCard
                  accentClassName="border-rose-500/25 text-rose-400"
                  icon={<TrendingDown className="size-4 stroke-[2.1]" />}
                  label="Expenses"
                  value={formatSignedSnapshotValue(-snapshot.expenseMinor, account.currency, "-")}
                />
              </div>
            </div>

            <div className="grid gap-4">
              <InfoMetricCard
                description="Captured entries linked to this account."
                label="Transaction count"
                value={`${transactions.length}`}
              />
              <InfoMetricCard
                description={
                  latestActivity
                    ? latestActivity.description || getTransactionLabel(latestActivity.type)
                    : "This account has no recent transactions."
                }
                icon={<Clock3 className="size-4 stroke-[2]" />}
                label="Latest activity"
                value={latestActivity ? formatDate(latestActivity.occurred_on) : "No activity yet"}
              />
            </div>
          </div>

          <div
            className="mt-8 border-t border-white/7 pt-8"
          />
          <section>
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <div className="flex items-center gap-3">
                  <h2 className="text-[2.1rem] leading-none font-black tracking-[-0.05em] text-foreground">
                    Recent activity
                  </h2>
                  <span className="inline-flex min-w-10 items-center justify-center rounded-full border border-white/8 bg-white/4 px-3 py-2 text-[1rem] font-medium text-muted-foreground">
                    {recentTransactions.length}
                  </span>
                </div>
                <p className="mt-4 text-[1.02rem] text-muted-foreground">
                  Latest transactions tied to this account, updated dynamically.
                </p>
              </div>
            </div>

            <div className="mt-7 grid gap-4">
              {transactionsQuery.isLoading ? (
                <p className="text-sm text-muted-foreground">Loading transactions...</p>
              ) : recentTransactions.length === 0 ? (
                <div className="rounded-[1.8rem] border border-dashed border-white/8 bg-white/[0.03] px-6 py-10 text-center">
                  <p className="text-base font-medium">No transactions found for this account.</p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Recent activity will appear here once this account has ledger entries.
                  </p>
                </div>
              ) : (
                recentTransactions.map((transaction, index) => {
                  const accountAmount = getAccountAmount(transaction, account.id)

                  return (
                    <div
                      className="rounded-[1.7rem] border border-white/7 bg-[linear-gradient(180deg,rgba(255,255,255,0.022),rgba(255,255,255,0.01))] px-5 py-5 shadow-[0_20px_36px_-32px_rgba(0,0,0,0.95)]"
                      key={transaction.id}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex min-w-0 items-start gap-4">
                          <span className="mt-0.5 inline-flex size-8 shrink-0 items-center justify-center rounded-full border border-white/8 bg-background/70 text-xs font-semibold text-muted-foreground">
                            {index + 1}
                          </span>
                          <div className="min-w-0">
                            <p className="truncate text-[1.3rem] leading-none font-black tracking-[-0.03em] text-foreground">
                              {transaction.description || getTransactionLabel(transaction.type)}
                            </p>
                            <p className="mt-3 text-[0.98rem] font-medium uppercase tracking-[0.06em] text-muted-foreground">
                              {formatDate(transaction.occurred_on)} ·{" "}
                              {getTransactionLabel(transaction.type)}
                            </p>
                          </div>
                        </div>
                        <p
                          className={cn(
                            "shrink-0 text-[1.05rem] font-black",
                            accountAmount < 0 ? "text-rose-400" : "text-emerald-400",
                          )}
                        >
                          {formatMoney(accountAmount, account.currency)}
                        </p>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </section>
        </div>
      </div>
    </section>
  )
}

function SnapshotMetricCard({
  label,
  value,
  icon,
  accentClassName,
}: {
  label: string
  value: string
  icon: ReactNode
  accentClassName?: string
}) {
  return (
    <div
      className={cn(
        "rounded-[1.6rem] border bg-[linear-gradient(180deg,rgba(255,255,255,0.015),rgba(255,255,255,0.008))] px-5 py-5",
        accentClassName,
      )}
    >
      <p className="inline-flex items-center gap-2 text-[0.82rem] font-bold uppercase tracking-[0.3em]">
        {icon}
        {label}
      </p>
      <p className="mt-5 text-[2.05rem] leading-none font-black tracking-[-0.05em] text-foreground">
        {value}
      </p>
    </div>
  )
}

function InfoMetricCard({
  label,
  value,
  description,
  icon,
}: {
  label: string
  value: string
  description: string
  icon?: ReactNode
}) {
  return (
    <div className="rounded-[1.9rem] border border-white/7 bg-background/72 px-5 py-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
      <p className="inline-flex items-center gap-2 text-[0.82rem] font-bold uppercase tracking-[0.32em] text-amber-300">
        {icon}
        {label}
      </p>
      <p className="mt-5 text-[2.7rem] leading-none font-black tracking-[-0.06em] text-foreground">
        {value}
      </p>
      <p className="mt-4 text-[1rem] text-muted-foreground">{description}</p>
    </div>
  )
}

function summarizeAccountActivity(
  transactions: Array<TransactionResponse>,
  accountId: string,
): ActivitySnapshot {
  return transactions.reduce<ActivitySnapshot>(
    (summary, transaction) => {
      const amountMinor = getAccountAmount(transaction, accountId)

      if (amountMinor > 0) {
        summary.incomeMinor += amountMinor
      }

      if (amountMinor < 0) {
        summary.expenseMinor += Math.abs(amountMinor)
      }

      return summary
    },
    { incomeMinor: 0, expenseMinor: 0 },
  )
}

function sortRecentTransactions(transactions: Array<TransactionResponse>) {
  return [...transactions].sort((left, right) => {
    const occurredOrder = right.occurred_on.localeCompare(left.occurred_on)

    if (occurredOrder !== 0) {
      return occurredOrder
    }

    return right.created_on.localeCompare(left.created_on)
  })
}

function getAccountAmount(transaction: TransactionResponse, accountId: string) {
  return (
    transaction.postings.find((posting) => posting.account_id === accountId)?.amount_minor ?? 0
  )
}

function getAccountSummaryDescription(type: AccountTypeValue, isArchived: boolean) {
  if (isArchived) {
    return "Archived overview of current balance, cash flow, and recent account activity."
  }

  return "Dynamic overview of current balance, cash flow, and recent account activity."
}

function formatSignedSnapshotValue(
  amountMinor: number,
  currency: string,
  zeroSign: "+" | "-",
) {
  if (amountMinor === 0) {
    return `${zeroSign}${formatMoney(0, currency)}`
  }

  const sign = amountMinor > 0 ? "+" : "-"
  return `${sign}${formatMoney(Math.abs(amountMinor), currency)}`
}

function getTransactionLabel(type: TransactionResponse["type"]) {
  switch (type) {
    case "expense":
      return "Expense"
    case "income":
      return "Income"
    case "transfer":
      return "Transfer"
    case "adjustment":
      return "Adjustment"
  }
}
