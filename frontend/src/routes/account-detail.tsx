import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link, useParams } from "@tanstack/react-router"
import { useState } from "react"
import type { AccountResponse } from "@/client"
import {
  AccountIcon,
  getAccountColorTheme,
  getAccountTypeLabel,
} from "@/components/accounts/account-appearance"
import {
  AccountFactList,
  AccountFactRow,
  AccountSectionCard,
  AccountSectionStack,
  AccountSplitLayout,
} from "@/components/accounts/account-layout"
import { AccountProfileForm } from "@/components/accounts/account-profile-form"
import { WithdrawForm } from "@/components/accounts/withdraw-form"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { getApiErrorMessage } from "@/lib/api-errors"
import {
  accountDetailOptions,
  accountKeys,
  closeAccount,
  upsertAccountInList,
  updateAccountProfile,
  withdrawFromAccount,
} from "@/lib/accounts"
import { formatDate, formatMoney } from "@/lib/format"
import { cn } from "@/lib/utils"

function formatAccountReference(accountId: string) {
  if (accountId.length <= 16) {
    return accountId
  }

  return `${accountId.slice(0, 10)}…${accountId.slice(-6)}`
}

export function AccountDetailRoute() {
  const { accountId } = useParams({ from: "/accounts/$accountId" })
  const queryClient = useQueryClient()
  const [withdrawErrorMessage, setWithdrawErrorMessage] = useState<string>()
  const [profileErrorMessage, setProfileErrorMessage] = useState<string>()
  const [closeErrorMessage, setCloseErrorMessage] = useState<string>()
  const accountQuery = useQuery(accountDetailOptions(accountId))

  const withdrawMutation = useMutation({
    mutationFn: (values: { amount_minor: number; currency: string }) =>
      withdrawFromAccount(accountId, values),
    onSuccess: async (account) => {
      setWithdrawErrorMessage(undefined)
      await syncAccount(account)
    },
  })
  const updateProfileMutation = useMutation({
    mutationFn: (values: {
      name: string
      type: "card" | "cash" | "bank" | "wallet" | "platform" | "savings" | "other"
      color_key?: string
    }) => updateAccountProfile(accountId, values),
    onSuccess: async (account) => {
      setProfileErrorMessage(undefined)
      await syncAccount(account)
    },
  })
  const closeMutation = useMutation({
    mutationFn: () => closeAccount(accountId),
    onSuccess: async (account) => {
      setCloseErrorMessage(undefined)
      await syncAccount(account)
    },
  })

  async function syncAccount(account: AccountResponse) {
    queryClient.setQueryData(accountKeys.detail(accountId), account)
    queryClient.setQueryData<Array<AccountResponse>>(
      accountKeys.list(),
      (accounts) => upsertAccountInList(accounts, account),
    )
    await queryClient.invalidateQueries({ queryKey: accountKeys.list() })
  }

  async function handleWithdraw(values: {
    amount_minor: number
    currency: string
  }) {
    setWithdrawErrorMessage(undefined)

    try {
      await withdrawMutation.mutateAsync(values)
    } catch (error) {
      setWithdrawErrorMessage(getApiErrorMessage(error))
    }
  }

  async function handleProfileUpdate(values: {
    name: string
    type: "card" | "cash" | "bank" | "wallet" | "platform" | "savings" | "other"
    color_key?: string
  }) {
    setProfileErrorMessage(undefined)

    try {
      await updateProfileMutation.mutateAsync(values)
    } catch (error) {
      setProfileErrorMessage(getApiErrorMessage(error))
    }
  }

  async function handleCloseAccount() {
    setCloseErrorMessage(undefined)

    try {
      await closeMutation.mutateAsync()
    } catch (error) {
      setCloseErrorMessage(getApiErrorMessage(error))
    }
  }

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
  const theme = getAccountColorTheme(account?.type ?? "card", account?.color_key)

  if (!account) {
    return (
      <section className="rounded-xl border bg-card p-8 shadow-sm">
        <p className="text-lg font-semibold">Account data is unavailable.</p>
      </section>
    )
  }

  return (
    <AccountSplitLayout>
      <Card className="gap-0 overflow-hidden py-0">
        <CardHeader
          className={cn(
            "relative overflow-hidden rounded-t-xl border-b px-0 pb-0 pt-0",
            theme.borderClassName,
          )}
        >
          <div
            className={cn(
              "absolute inset-0 bg-gradient-to-r",
              theme.previewGlowClassName,
            )}
          />
          <div className="relative grid gap-5 px-6 pb-6 pt-6 md:grid-cols-[auto_minmax(0,1fr)] md:items-center">
            <div
              className={cn(
                "flex size-14 shrink-0 items-center justify-center rounded-2xl md:size-16",
                theme.iconWrapClassName,
              )}
            >
              <AccountIcon type={account.type} className="size-6 md:size-7" />
            </div>
            <div className="min-w-0 self-center">
              <CardTitle>{account.name}</CardTitle>
              <div className="mt-3 flex flex-wrap items-center gap-2">
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
                <span className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                  {account.status}
                </span>
              </div>
            </div>
            <CardDescription className="flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-border/60 pt-4 md:col-start-2 md:pt-3">
              <span>Account ID {formatAccountReference(account.id)}</span>
              <span aria-hidden="true">·</span>
              <span>Opened {formatDate(account.opened_on)}</span>
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="grid gap-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border bg-muted/40 p-4">
              <p className="text-sm text-muted-foreground">Current balance</p>
              <p className="mt-2 text-3xl font-semibold">
                {formatMoney(
                  account.current_balance.amount_minor,
                  account.current_balance.currency,
                )}
              </p>
            </div>
            <div className="rounded-lg border bg-muted/20 p-4">
              <AccountFactList>
                <AccountFactRow
                  label="Type"
                  value={getAccountTypeLabel(account.type)}
                />
                <AccountFactRow label="Currency" value={account.currency} />
                <AccountFactRow
                  label="Opened on"
                  value={formatDate(account.opened_on)}
                />
                <AccountFactRow
                  label="Closed on"
                  value={account.closed_on ? formatDate(account.closed_on) : "Open"}
                />
              </AccountFactList>
            </div>
          </div>

          <div>
            <Link
              className="text-sm font-medium text-primary hover:underline"
              to="/accounts"
            >
              Back to accounts
            </Link>
          </div>
        </CardContent>
      </Card>

      <AccountSectionStack>
        <AccountSectionCard
          description="Edit the account name, type, and appearance used across the app."
          title="Account profile"
        >
          <AccountProfileForm
            account={account}
            errorMessage={profileErrorMessage}
            isPending={updateProfileMutation.isPending}
            onSubmit={handleProfileUpdate}
          />
        </AccountSectionCard>

        <AccountSectionCard
          description={
            account.status === "closed"
              ? "Closed accounts keep their final balance and cannot move money."
              : "Enter an amount like 25 or 25.50 to withdraw from this account."
          }
          title={account.status === "closed" ? "Balance is locked" : "Withdraw money"}
        >
          {account.status === "closed" ? (
            <div className="rounded-[1.6rem] border border-border/70 bg-muted/15 p-5">
              <p className="text-sm text-muted-foreground">
                This account is closed and cannot accept new balance changes.
              </p>
            </div>
          ) : (
            <WithdrawForm
              currency={account.currency}
              errorMessage={withdrawErrorMessage}
              isPending={withdrawMutation.isPending}
              onSubmit={handleWithdraw}
            />
          )}
        </AccountSectionCard>

        <AccountSectionCard
          description={
            account.status === "closed"
              ? "This account is already closed."
              : "This keeps history but blocks future balance changes."
          }
          footer={
            account.status === "active" ? (
              <button
                className="inline-flex rounded-full border border-destructive/40 px-4 py-2 text-sm font-semibold text-destructive transition hover:bg-destructive/10"
                disabled={closeMutation.isPending}
                onClick={() => void handleCloseAccount()}
                type="button"
              >
                {closeMutation.isPending ? "Closing..." : "Close account"}
              </button>
            ) : undefined
          }
          title="Close account"
        >
          {closeErrorMessage ? (
            <p className="rounded-2xl border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {closeErrorMessage}
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">
              {account.status === "closed"
                ? "Closed accounts stay visible with their final balance."
                : "After closing, deposits and withdrawals will no longer be available."}
            </p>
          )}
        </AccountSectionCard>
      </AccountSectionStack>
    </AccountSplitLayout>
  )
}
