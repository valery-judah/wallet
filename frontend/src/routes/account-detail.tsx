import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link, useParams } from "@tanstack/react-router"
import { useState } from "react"
import type { AccountResponse } from "@/client"
import {
  AccountIcon,
  getAccountColorTheme,
  getAccountTypeLabel,
} from "@/components/accounts/account-appearance"
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
      icon_key?: string
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
    icon_key?: string
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
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
      <Card>
        <CardHeader
          className={cn(
            "relative overflow-hidden rounded-t-xl border-b",
            theme.borderClassName,
          )}
        >
          <div
            className={cn(
              "absolute inset-x-0 top-0 h-20 bg-gradient-to-r",
              theme.previewGlowClassName,
            )}
          />
          <div className="relative flex items-start gap-4">
            <div
              className={cn(
                "flex size-14 shrink-0 items-center justify-center rounded-2xl",
                theme.iconWrapClassName,
              )}
            >
              <AccountIcon type={account.type} iconKey={account.icon_key} className="size-6" />
            </div>
            <div className="min-w-0">
              <CardTitle>{account.name}</CardTitle>
              <div className="mt-2 flex flex-wrap items-center gap-2">
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
          </div>
          <CardDescription>
            Account ID: {account.id} · Opened {formatDate(account.opened_on)}
          </CardDescription>
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
              <dl className="grid gap-3 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-muted-foreground">Type</dt>
                  <dd className="font-medium">{getAccountTypeLabel(account.type)}</dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-muted-foreground">Currency</dt>
                  <dd className="font-medium">{account.currency}</dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-muted-foreground">Opened on</dt>
                  <dd className="font-medium">{formatDate(account.opened_on)}</dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-muted-foreground">Closed on</dt>
                  <dd className="font-medium">
                    {account.closed_on ? formatDate(account.closed_on) : "Open"}
                  </dd>
                </div>
              </dl>
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

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Account profile</CardTitle>
            <CardDescription>
              Edit the account identity and display metadata used across the app.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <AccountProfileForm
              account={account}
              errorMessage={profileErrorMessage}
              isPending={updateProfileMutation.isPending}
              onSubmit={handleProfileUpdate}
            />
            {account.status === "active" ? (
              <div className="mt-6 rounded-[1.6rem] border border-border/70 bg-muted/15 p-5">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <p className="font-semibold">Close account</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      This keeps history but blocks future balance changes.
                    </p>
                  </div>
                  <button
                    className="inline-flex rounded-full border border-destructive/40 px-4 py-2 text-sm font-semibold text-destructive transition hover:bg-destructive/10"
                    disabled={closeMutation.isPending}
                    onClick={() => void handleCloseAccount()}
                    type="button"
                  >
                    {closeMutation.isPending ? "Closing..." : "Close account"}
                  </button>
                </div>
                {closeErrorMessage ? (
                  <p className="mt-4 rounded-2xl border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                    {closeErrorMessage}
                  </p>
                ) : null}
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              {account.status === "closed" ? "Balance is locked" : "Withdraw money"}
            </CardTitle>
            <CardDescription>
              {account.status === "closed"
                ? "Closed accounts keep their final balance and cannot move money."
                : "Enter an amount in minor units to withdraw from this account."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {account.status === "closed" ? (
              <div className="rounded-[1.6rem] border border-border/70 bg-muted/15 p-5">
                <p className="text-sm text-muted-foreground">
                  Reopening is not part of the MVP account lifecycle.
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
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
