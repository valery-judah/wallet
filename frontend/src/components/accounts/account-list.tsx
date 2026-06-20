import { Link } from "@tanstack/react-router"
import type { AccountResponse } from "@/client"
import {
  AccountIcon,
  getAccountColorTheme,
  getAccountTypeLabel,
} from "@/components/accounts/account-appearance"
import { formatDate, formatMoney } from "@/lib/format"
import { cn } from "@/lib/utils"

type AccountListProps = {
  accounts: Array<AccountResponse>
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

  return (
    <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
      {accounts.map((account) => {
        const theme = getAccountColorTheme(account.type, account.color_key)

        return (
          <article
            className={cn(
              "surface relative overflow-hidden rounded-[2rem] border p-6",
              theme.borderClassName,
            )}
            key={account.id}
          >
            <div
              className={cn(
                "absolute inset-x-0 top-0 h-18 bg-gradient-to-r",
                theme.previewGlowClassName,
              )}
            />
            <div className="relative flex items-start justify-between gap-4">
              <div className="flex min-w-0 items-start gap-4">
                <div
                  className={cn(
                    "flex size-12 shrink-0 items-center justify-center rounded-2xl",
                    theme.iconWrapClassName,
                  )}
                >
                  <AccountIcon type={account.type} iconKey={account.icon_key} />
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={cn(
                        "rounded-full px-3 py-1 text-xs font-semibold",
                        theme.badgeClassName,
                      )}
                    >
                      {getAccountTypeLabel(account.type)}
                    </span>
                    <span className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                      {account.currency}
                    </span>
                  </div>
                  <h2 className="mt-3 truncate text-2xl font-semibold">
                    {account.name}
                  </h2>
                </div>
              </div>
              <span
                className={cn(
                  "rounded-full px-3 py-1 text-xs font-semibold",
                  account.status === "closed"
                    ? "bg-slate-500/12 text-slate-200"
                    : theme.badgeClassName,
                )}
              >
                {account.status}
              </span>
            </div>

            <p className="relative mt-8 text-3xl font-semibold">
              {formatMoney(
                account.current_balance.amount_minor,
                account.current_balance.currency,
              )}
            </p>
            <p className="relative mt-2 text-sm text-muted-foreground">
              {account.status === "closed" && account.closed_on
                ? `Closed ${formatDate(account.closed_on)}`
                : `Opened ${formatDate(account.opened_on)}`}
            </p>

            <Link
              className="relative mt-8 inline-flex rounded-full border border-border px-4 py-2 text-sm font-semibold text-foreground transition hover:bg-accent"
              params={{ accountId: account.id }}
              to="/accounts/$accountId"
            >
              Open account
            </Link>
          </article>
        )
      })}
    </section>
  )
}
