import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link, useParams } from "@tanstack/react-router"
import { useState } from "react"
import type { AccountResponse, TransactionResponse } from "@/client"
import {
  AccountIcon,
  type AccountTypeValue,
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
import { TransactionComposer } from "@/components/accounts/transaction-composer"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { getApiErrorMessage } from "@/lib/api-errors"
import {
  archiveAccount,
  accountDetailOptions,
  accountKeys,
  accountsListOptions,
  upsertAccountInList,
  updateAccountProfile,
} from "@/lib/accounts"
import { formatDate, formatMoney } from "@/lib/format"
import { incomeCategoriesTreeOptions } from "@/lib/income-categories"
import { spendingCategoriesTreeOptions } from "@/lib/spending-categories"
import {
  createTransaction,
  transactionKeys,
  transactionsListOptions,
} from "@/lib/transactions"
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
  const [transactionErrorMessage, setTransactionErrorMessage] = useState<string>()
  const [profileErrorMessage, setProfileErrorMessage] = useState<string>()
  const [archiveErrorMessage, setArchiveErrorMessage] = useState<string>()
  const accountQuery = useQuery(accountDetailOptions(accountId))
  const accountsQuery = useQuery(accountsListOptions())
  const spendingCategoriesQuery = useQuery(spendingCategoriesTreeOptions())
  const incomeCategoriesQuery = useQuery(incomeCategoriesTreeOptions())
  const transactionsQuery = useQuery(transactionsListOptions(accountId))

  const transactionMutation = useMutation({
    mutationFn: createTransaction,
    onSuccess: async () => {
      setTransactionErrorMessage(undefined)
      await refreshAccountState()
    },
  })
  const updateProfileMutation = useMutation({
    mutationFn: (values: {
      name: string
      type: AccountTypeValue
      color_key?: string
    }) => updateAccountProfile(accountId, values),
    onSuccess: async (account) => {
      setProfileErrorMessage(undefined)
      await syncAccount(account)
    },
  })
  const archiveMutation = useMutation({
    mutationFn: () => archiveAccount(accountId),
    onSuccess: async (account) => {
      setArchiveErrorMessage(undefined)
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

  async function refreshAccountState() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: accountKeys.detail(accountId) }),
      queryClient.invalidateQueries({ queryKey: accountKeys.list() }),
      queryClient.invalidateQueries({ queryKey: transactionKeys.list(accountId) }),
    ])
  }

  async function handleTransactionSubmit(values: Parameters<typeof createTransaction>[0]) {
    setTransactionErrorMessage(undefined)

    try {
      await transactionMutation.mutateAsync(values)
    } catch (error) {
      setTransactionErrorMessage(getApiErrorMessage(error))
    }
  }

  async function handleProfileUpdate(values: {
    name: string
    type: AccountTypeValue
    color_key?: string
  }) {
    setProfileErrorMessage(undefined)

    try {
      await updateProfileMutation.mutateAsync(values)
    } catch (error) {
      setProfileErrorMessage(getApiErrorMessage(error))
    }
  }

  async function handleArchiveAccount() {
    setArchiveErrorMessage(undefined)

    try {
      await archiveMutation.mutateAsync()
    } catch (error) {
      setArchiveErrorMessage(getApiErrorMessage(error))
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
  const theme = getAccountColorTheme(account?.type ?? "debit_card", account?.color_key)
  const isArchived = account?.archived_at != null

  if (!account) {
    return (
      <section className="rounded-xl border bg-card p-8 shadow-sm">
        <p className="text-lg font-semibold">Account data is unavailable.</p>
      </section>
    )
  }

  const accounts = accountsQuery.data ?? []
  const spendingCategories = spendingCategoriesQuery.data ?? []
  const incomeCategories = incomeCategoriesQuery.data ?? []
  const transactions = transactionsQuery.data ?? []

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
                    {isArchived ? "archived" : "active"}
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
                  label="Archived at"
                  value={account.archived_at ? formatDate(account.archived_at) : "Active"}
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
            isArchived
              ? "Archived accounts keep their final balance and cannot post new transactions."
              : "Record expense, income, transfers, or manual adjustments directly into the ledger."
          }
          title={isArchived ? "Ledger is locked" : "Record transaction"}
        >
          {isArchived ? (
            <div className="rounded-[1.6rem] border border-border/70 bg-muted/15 p-5">
              <p className="text-sm text-muted-foreground">
                This account is archived and cannot accept new transactions.
              </p>
            </div>
          ) : (
            <TransactionComposer
              account={account}
              accounts={accounts}
              incomeCategories={incomeCategories}
              errorMessage={transactionErrorMessage}
              isPending={transactionMutation.isPending}
              onSubmit={handleTransactionSubmit}
              spendingCategories={spendingCategories}
            />
          )}
        </AccountSectionCard>

        <AccountSectionCard
          description="Recent ledger activity for this account."
          title="Recent activity"
        >
          {transactionsQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading transactions...</p>
          ) : transactions.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No transactions yet for this account.
            </p>
          ) : (
            <div className="grid gap-3">
              {transactions.map((transaction) => {
                const accountAmount = getAccountAmount(transaction, account.id)
                return (
                  <div
                    className="rounded-[1.4rem] border border-border/70 bg-background/40 px-4 py-3"
                    key={transaction.id}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="font-medium">
                          {transaction.description || getTransactionLabel(transaction.type)}
                        </p>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {formatDate(transaction.occurred_on)} · {transaction.type}
                        </p>
                      </div>
                      <p className="text-sm font-semibold">
                        {formatMoney(accountAmount, account.currency)}
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </AccountSectionCard>

        <AccountSectionCard
          description={
            isArchived ? "This account is already archived." : "This keeps history but blocks future transactions."
          }
          footer={
            !isArchived ? (
              <button
                className="inline-flex rounded-full border border-destructive/40 px-4 py-2 text-sm font-semibold text-destructive transition hover:bg-destructive/10"
                disabled={archiveMutation.isPending}
                onClick={() => void handleArchiveAccount()}
                type="button"
              >
                {archiveMutation.isPending ? "Archiving..." : "Archive account"}
              </button>
            ) : undefined
          }
          title="Archive account"
        >
          {archiveErrorMessage ? (
            <p className="rounded-2xl border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {archiveErrorMessage}
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">
              {isArchived
                ? "Archived accounts stay visible with their final balance."
                : "After archiving, new ledger entries will no longer be allowed for this account."}
            </p>
          )}
        </AccountSectionCard>
      </AccountSectionStack>
    </AccountSplitLayout>
  )
}

function getAccountAmount(transaction: TransactionResponse, accountId: string) {
  return (
    transaction.postings.find((posting) => posting.account_id === accountId)?.amount_minor ?? 0
  )
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
