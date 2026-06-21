import { Link } from "@tanstack/react-router"
import {
  ArrowUpRight,
  PencilLine,
  TrendingUp,
} from "lucide-react"
import type { AccountResponse } from "@/client"
import {
  AccountIcon,
  getAccountColorTheme,
  getAccountTypeLabel,
} from "@/components/accounts/account-appearance"
import { formatMoney } from "@/lib/format"
import { cn } from "@/lib/utils"

type AccountListProps = {
  accounts: Array<AccountResponse>
}

function orderAccounts(accounts: Array<AccountResponse>) {
  return [...accounts].sort((left, right) => {
    const archivedRank = Number(left.archived_at !== null) - Number(right.archived_at !== null)

    if (archivedRank !== 0) {
      return archivedRank
    }

    return left.name.localeCompare(right.name)
  })
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

  const orderedAccounts = orderAccounts(accounts)

  return (
    <section className="grid gap-4 xl:grid-cols-2">
      {orderedAccounts.map((account) => {
        const theme = getAccountColorTheme(account.type, account.color_key)

        return (
          <Link
            className={cn(
              "group relative block overflow-hidden rounded-[1.55rem] border border-white/8 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.045),transparent_28%),linear-gradient(135deg,rgba(255,255,255,0.015),rgba(255,255,255,0))] bg-card px-5 py-5 shadow-[0_16px_38px_-30px_rgba(0,0,0,0.9)] transition duration-200 hover:border-white/12 hover:bg-card/95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-2 focus-visible:ring-offset-background md:px-6 md:py-6",
              theme.borderClassName,
            )}
            key={account.id}
            params={{ accountId: account.id }}
            to="/accounts/$accountId"
          >
            <div
              className={cn(
                "absolute inset-x-0 top-0 h-[0.62rem] bg-gradient-to-r",
                theme.previewGlowClassName,
              )}
            />
            <div className="absolute inset-x-0 bottom-0 h-14 bg-gradient-to-t from-black/8 to-transparent" />
            <div className="relative flex min-h-[10.75rem] flex-col">
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-3">
                  <div
                    className={cn(
                      "mt-0.5 flex size-12 shrink-0 items-center justify-center rounded-[1rem] shadow-[0_8px_20px_-16px_rgba(0,0,0,0.95)]",
                      theme.iconWrapClassName,
                    )}
                  >
                    <AccountIcon className="size-5" type={account.type} />
                  </div>
                  <div className="min-w-0">
                    <h2 className="truncate text-[1.45rem] leading-none font-black tracking-[-0.045em] md:text-[1.6rem]">
                      {account.name}
                    </h2>
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                      <span className="rounded-full border border-white/8 bg-black/10 px-2 py-0.5 text-[0.64rem] font-medium text-foreground/88">
                        {getAccountTypeLabel(account.type)}
                      </span>
                      <span className="text-[0.74rem] font-bold tracking-[0.02em] text-muted-foreground">
                        {account.currency}
                      </span>
                      {account.archived_at ? (
                        <span className="rounded-full border border-white/8 bg-white/5 px-2 py-0.5 text-[0.64rem] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                          Archived
                        </span>
                      ) : null}
                    </div>
                  </div>
                </div>
                {account.archived_at ? null : (
                  <span
                    aria-hidden="true"
                    className="mt-0.5 inline-flex size-7 items-center justify-center rounded-full text-muted-foreground transition group-hover:text-foreground"
                    data-testid={`account-edit-affordance-${account.id}`}
                  >
                    <PencilLine aria-hidden="true" className="size-[0.95rem] stroke-[1.9]" />
                  </span>
                )}
              </div>

              <div className="mt-auto pt-4">
                <p className="text-[1.7rem] leading-none font-black tracking-[-0.045em] text-foreground md:text-[1.85rem]">
                  {formatMoney(
                    account.current_balance.amount_minor,
                    account.current_balance.currency,
                  )}
                </p>
                <div className="mt-4 flex items-center justify-between gap-2">
                  <span className="inline-flex items-center gap-1.5 text-[0.82rem] font-bold text-emerald-400">
                    <TrendingUp className="size-3 stroke-[2.1]" />
                    Healthy Status
                  </span>
                  <span className="inline-flex items-center gap-1 text-[0.82rem] font-bold text-amber-300">
                    Details
                    <ArrowUpRight className="size-3 stroke-[2.1]" />
                  </span>
                </div>
              </div>
            </div>
          </Link>
        )
      })}
    </section>
  )
}
