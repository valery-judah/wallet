import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { ArrowUpRight, Landmark, ReceiptText, Wallet } from "lucide-react"
import { FormEvent, type ReactNode, useEffect, useState } from "react"
import type { AccountResponse, SpendingCategoryResponse, TransactionResponse } from "@/client"
import { PageIntro, SectionCard, SectionStack, SplitLayout } from "@/components/layout/page-layout"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { getApiErrorMessage } from "@/lib/api-errors"
import { accountKeys, accountsListOptions } from "@/lib/accounts"
import { formatDate, formatMoney } from "@/lib/format"
import { parseMajorAmount } from "@/lib/money"
import { spendingCategoriesTreeOptions } from "@/lib/spending-categories"
import {
  createTransaction,
  transactionKeys,
  transactionsListOptions,
} from "@/lib/transactions"

type FlatCategory = {
  id: string
  name: string
  label: string
}

export function TransactionsRoute() {
  const queryClient = useQueryClient()
  const accountsQuery = useQuery(accountsListOptions())
  const categoriesQuery = useQuery(spendingCategoriesTreeOptions())
  const transactionsQuery = useQuery(transactionsListOptions())
  const [accountId, setAccountId] = useState("")
  const [categoryId, setCategoryId] = useState("")
  const [amountInput, setAmountInput] = useState("")
  const [occurredOn, setOccurredOn] = useState(new Date().toISOString().slice(0, 10))
  const [merchantName, setMerchantName] = useState("")
  const [description, setDescription] = useState("")
  const [errorMessage, setErrorMessage] = useState<string>()
  const [successMessage, setSuccessMessage] = useState<string>()

  const activeAccounts = (accountsQuery.data ?? []).filter((account) => account.archived_at == null)
  const spendingCategories = flattenSpendingCategories(categoriesQuery.data ?? [])
  const selectedAccount = activeAccounts.find((account) => account.id === accountId)
  const selectedCategory = spendingCategories.find((category) => category.id === categoryId)
  const parsedAmount = parseMajorAmount(amountInput, selectedAccount?.currency ?? "ARS")
  const showAmountError =
    amountInput.trim().length > 0 && parsedAmount.amountMinor === undefined
  const amountErrorMessage =
    amountInput.trim().length > 0 ? parsedAmount.error : "Enter a positive amount."
  const recentWithdrawals = sortRecentTransactions(
    (transactionsQuery.data ?? []).filter((transaction) => transaction.type === "expense"),
  ).slice(0, 8)

  useEffect(() => {
    if (activeAccounts.length === 0) {
      if (accountId !== "") {
        setAccountId("")
      }
      return
    }

    if (!activeAccounts.some((account) => account.id === accountId)) {
      setAccountId(activeAccounts[0]?.id ?? "")
    }
  }, [accountId, activeAccounts])

  useEffect(() => {
    if (spendingCategories.length === 0) {
      if (categoryId !== "") {
        setCategoryId("")
      }
      return
    }

    if (!spendingCategories.some((category) => category.id === categoryId)) {
      setCategoryId(spendingCategories[0]?.id ?? "")
    }
  }, [categoryId, spendingCategories])

  const createTransactionMutation = useMutation({
    mutationFn: createTransaction,
    onSuccess: async (_, variables) => {
      const selectedAccountId = variables.postings.find((posting) => posting.account_id)?.account_id

      await queryClient.invalidateQueries({ queryKey: transactionKeys.all })
      await queryClient.invalidateQueries({ queryKey: accountKeys.list() })

      if (selectedAccountId) {
        await queryClient.invalidateQueries({
          queryKey: accountKeys.detail(selectedAccountId),
        })
      }
    },
  })

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErrorMessage(undefined)
    setSuccessMessage(undefined)

    if (!selectedAccount) {
      setErrorMessage("Choose an active account.")
      return
    }

    if (!selectedCategory) {
      setErrorMessage("Choose a spending category.")
      return
    }

    if (parsedAmount.amountMinor === undefined) {
      setErrorMessage(parsedAmount.error)
      return
    }

    try {
      await createTransactionMutation.mutateAsync({
        type: "expense",
        occurred_on: occurredOn || undefined,
        description: description.trim() || merchantName.trim() || selectedCategory.name,
        merchant_name: merchantName.trim() || undefined,
        postings: [
          {
            account_id: selectedAccount.id,
            amount_minor: -parsedAmount.amountMinor,
            currency: selectedAccount.currency,
          },
          {
            category_id: selectedCategory.id,
            amount_minor: parsedAmount.amountMinor,
            currency: selectedAccount.currency,
          },
        ],
      })

      setAmountInput("")
      setMerchantName("")
      setDescription("")
      setSuccessMessage(
        `Recorded ${formatMoney(parsedAmount.amountMinor, selectedAccount.currency)} from ${selectedAccount.name}.`,
      )
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error))
    }
  }

  if (accountsQuery.isLoading || categoriesQuery.isLoading) {
    return (
      <section className="rounded-[2rem] border bg-card p-8 shadow-sm">
        <p className="text-lg font-semibold">Loading transactions...</p>
      </section>
    )
  }

  if (accountsQuery.isError || categoriesQuery.isError) {
    return (
      <section className="rounded-[2rem] border bg-card p-8 shadow-sm">
        <p className="text-lg font-semibold">Unable to load the withdraw flow.</p>
        <p className="mt-2 text-sm text-destructive">
          {getApiErrorMessage(accountsQuery.error ?? categoriesQuery.error)}
        </p>
      </section>
    )
  }

  const formDisabled = activeAccounts.length === 0 || spendingCategories.length === 0

  return (
    <SectionStack>
      <PageIntro
        eyebrow="Transactions"
        title="Withdraw from an account."
        description="Record an expense transaction as a withdraw flow: choose the account, classify the spend, and post it to the ledger."
      />

      <SplitLayout className="xl:grid-cols-[minmax(0,1.1fr)_360px]">
        <SectionCard
          title="New withdraw"
          description="Expense transactions credit a spending category and debit the selected account."
          footer={
            <div className="flex w-full items-center justify-between gap-4">
              <p className="text-sm text-muted-foreground">
                Posted immediately to the ledger for the selected account.
              </p>
              <Button disabled={formDisabled || createTransactionMutation.isPending} form="withdraw-form" type="submit">
                {createTransactionMutation.isPending ? "Posting..." : "Withdraw"}
              </Button>
            </div>
          }
        >
          <form className="grid gap-6" id="withdraw-form" onSubmit={handleSubmit}>
            {activeAccounts.length === 0 ? (
              <EmptySupportCard
                body="Create an active account before recording a withdrawal."
                ctaLabel="Create account"
                to="/accounts/new"
              />
            ) : null}

            {spendingCategories.length === 0 ? (
              <EmptySupportCard
                body="Add at least one spending category before recording a withdrawal."
                ctaLabel="Manage categories"
                to="/categories"
              />
            ) : null}

            <div className="grid gap-4 md:grid-cols-2">
              <FieldBlock>
                <Label htmlFor="withdraw-account">Account</Label>
                <select
                  className="border-input focus-visible:border-ring focus-visible:ring-ring/50 h-9 w-full rounded-md border bg-transparent px-3 py-1 text-sm outline-none focus-visible:ring-[3px] disabled:pointer-events-none disabled:opacity-50"
                  disabled={activeAccounts.length === 0}
                  id="withdraw-account"
                  onChange={(event) => setAccountId(event.target.value)}
                  value={accountId}
                >
                  {activeAccounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name} ({account.currency})
                    </option>
                  ))}
                </select>
                <p className="min-h-5 text-xs leading-5 text-muted-foreground">
                  Only active accounts accept new transactions.
                </p>
              </FieldBlock>

              <FieldBlock>
                <Label htmlFor="withdraw-category">Spending category</Label>
                <select
                  className="border-input focus-visible:border-ring focus-visible:ring-ring/50 h-9 w-full rounded-md border bg-transparent px-3 py-1 text-sm outline-none focus-visible:ring-[3px] disabled:pointer-events-none disabled:opacity-50"
                  disabled={spendingCategories.length === 0}
                  id="withdraw-category"
                  onChange={(event) => setCategoryId(event.target.value)}
                  value={categoryId}
                >
                  {spendingCategories.map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.label}
                    </option>
                  ))}
                </select>
                <p className="min-h-5 text-xs leading-5 text-muted-foreground">
                  Choose where this withdraw should land in the spending tree.
                </p>
              </FieldBlock>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <FieldBlock>
                <Label htmlFor="withdraw-amount">Amount</Label>
                <Input
                  aria-invalid={showAmountError ? true : undefined}
                  id="withdraw-amount"
                  inputMode="decimal"
                  onChange={(event) => setAmountInput(event.target.value)}
                  placeholder="12 or 12.50"
                  type="text"
                  value={amountInput}
                />
                <p
                  className={
                    showAmountError
                      ? "min-h-5 text-xs leading-5 text-destructive"
                      : "min-h-5 text-xs leading-5 text-muted-foreground"
                  }
                >
                  {amountErrorMessage}
                </p>
              </FieldBlock>

              <FieldBlock>
                <Label htmlFor="withdraw-date">Withdraw date</Label>
                <Input
                  id="withdraw-date"
                  onChange={(event) => setOccurredOn(event.target.value)}
                  type="date"
                  value={occurredOn}
                />
                <p className="min-h-5 text-xs leading-5 text-muted-foreground">
                  Transactions are created as posted on this date.
                </p>
              </FieldBlock>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <FieldBlock>
                <Label htmlFor="withdraw-merchant">Merchant</Label>
                <Input
                  id="withdraw-merchant"
                  onChange={(event) => setMerchantName(event.target.value)}
                  placeholder="Corner cafe, grocery store, ATM"
                  value={merchantName}
                />
                <p className="min-h-5 text-xs leading-5 text-muted-foreground">
                  Optional merchant label for the withdrawal.
                </p>
              </FieldBlock>

              <FieldBlock>
                <Label htmlFor="withdraw-description">Description</Label>
                <Input
                  id="withdraw-description"
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder="Coffee run, groceries, transport"
                  value={description}
                />
                <p className="min-h-5 text-xs leading-5 text-muted-foreground">
                  Falls back to the merchant or category name if left blank.
                </p>
              </FieldBlock>
            </div>

            {errorMessage ? (
              <p className="rounded-2xl border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                {errorMessage}
              </p>
            ) : null}

            {successMessage ? (
              <p className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-700 dark:text-emerald-300">
                {successMessage}
              </p>
            ) : null}
          </form>
        </SectionCard>

        <SectionStack>
          <SectionCard
            title="Withdraw summary"
            description="The new transaction will be balanced automatically."
          >
            <dl className="grid gap-4 text-sm">
              <SummaryRow
                icon={<Wallet className="size-4" />}
                label="Account"
                value={selectedAccount ? selectedAccount.name : "Choose an account"}
              />
              <SummaryRow
                icon={<ReceiptText className="size-4" />}
                label="Category"
                value={selectedCategory ? selectedCategory.name : "Choose a spending category"}
              />
              <SummaryRow
                icon={<ArrowUpRight className="size-4" />}
                label="Amount"
                value={
                  selectedAccount && parsedAmount.amountMinor !== undefined
                    ? formatMoney(parsedAmount.amountMinor, selectedAccount.currency)
                    : selectedAccount
                      ? formatMoney(0, selectedAccount.currency)
                      : "Choose an account"
                }
              />
              <SummaryRow
                icon={<Landmark className="size-4" />}
                label="Current balance"
                value={
                  selectedAccount
                    ? formatMoney(
                        selectedAccount.current_balance.amount_minor,
                        selectedAccount.current_balance.currency,
                      )
                    : "Choose an account"
                }
              />
            </dl>
          </SectionCard>

          <SectionCard
            title="Recent withdrawals"
            description="Latest expense transactions across all active accounts."
          >
            {transactionsQuery.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading recent withdrawals...</p>
            ) : transactionsQuery.isError ? (
              <p className="text-sm text-destructive">
                {getApiErrorMessage(transactionsQuery.error)}
              </p>
            ) : recentWithdrawals.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No withdrawals yet. Your first expense transaction will appear here.
              </p>
            ) : (
              <div className="grid gap-3">
                {recentWithdrawals.map((transaction) => (
                  <WithdrawCard
                    account={findAccountForTransaction(transaction, accountsQuery.data ?? [])}
                    category={findCategoryForTransaction(transaction, spendingCategories)}
                    key={transaction.id}
                    transaction={transaction}
                  />
                ))}
              </div>
            )}
          </SectionCard>
        </SectionStack>
      </SplitLayout>
    </SectionStack>
  )
}

function FieldBlock({ children }: { children: ReactNode }) {
  return <div className="grid content-start gap-2">{children}</div>
}

function SummaryRow({
  icon,
  label,
  value,
}: {
  icon: ReactNode
  label: string
  value: string
}) {
  return (
    <div className="flex items-start justify-between gap-4 rounded-2xl border border-border/60 bg-background/50 px-4 py-3">
      <div className="flex items-center gap-3">
        <span className="inline-flex size-8 items-center justify-center rounded-full border border-border/70 bg-background">
          {icon}
        </span>
        <dt className="text-muted-foreground">{label}</dt>
      </div>
      <dd className="text-right font-medium">{value}</dd>
    </div>
  )
}

function EmptySupportCard({
  body,
  ctaLabel,
  to,
}: {
  body: string
  ctaLabel: string
  to: "/accounts/new" | "/categories"
}) {
  return (
    <div className="rounded-[1.5rem] border border-dashed border-border/70 bg-background/40 p-4">
      <p className="text-sm text-muted-foreground">{body}</p>
      <Button asChild className="mt-3" size="sm" variant="outline">
        <Link to={to}>{ctaLabel}</Link>
      </Button>
    </div>
  )
}

function WithdrawCard({
  account,
  category,
  transaction,
}: {
  account?: AccountResponse
  category?: FlatCategory
  transaction: TransactionResponse
}) {
  const amountPosting = transaction.postings.find((posting) => posting.account_id)
  const currency = amountPosting?.currency ?? account?.currency ?? "ARS"
  const amountMinor = Math.abs(amountPosting?.amount_minor ?? 0)

  return (
    <article className="rounded-[1.4rem] border border-border/70 bg-background/45 px-4 py-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-foreground">
            {transaction.description || transaction.merchant_name || "Withdrawal"}
          </p>
          <p className="mt-1 text-xs uppercase tracking-[0.12em] text-muted-foreground">
            {formatDate(transaction.occurred_on)}
          </p>
        </div>
        <p className="shrink-0 text-sm font-semibold text-rose-500">
          {formatMoney(amountMinor, currency)}
        </p>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
        <span className="rounded-full border border-border/70 px-2.5 py-1">
          {account?.name ?? "Unknown account"}
        </span>
        <span className="rounded-full border border-border/70 px-2.5 py-1">
          {category?.name ?? "Unmapped category"}
        </span>
        {transaction.merchant_name ? (
          <span className="rounded-full border border-border/70 px-2.5 py-1">
            {transaction.merchant_name}
          </span>
        ) : null}
      </div>
    </article>
  )
}

function flattenSpendingCategories(
  categories: Array<SpendingCategoryResponse>,
  depth = 0,
): Array<FlatCategory> {
  return categories.flatMap((category) => [
    {
      id: category.id,
      name: category.name,
      label: `${depth > 0 ? `${"-- ".repeat(depth)}` : ""}${category.name}`,
    },
    ...flattenSpendingCategories(category.children ?? [], depth + 1),
  ])
}

function sortRecentTransactions(transactions: Array<TransactionResponse>) {
  return [...transactions].sort((left, right) => {
    const leftTimestamp = Date.parse(left.occurred_on || left.created_on)
    const rightTimestamp = Date.parse(right.occurred_on || right.created_on)

    if (leftTimestamp === rightTimestamp) {
      return Date.parse(right.created_on) - Date.parse(left.created_on)
    }

    return rightTimestamp - leftTimestamp
  })
}

function findAccountForTransaction(
  transaction: TransactionResponse,
  accounts: Array<AccountResponse>,
) {
  const accountId = transaction.postings.find((posting) => posting.account_id)?.account_id
  return accounts.find((account) => account.id === accountId)
}

function findCategoryForTransaction(
  transaction: TransactionResponse,
  categories: Array<FlatCategory>,
) {
  const categoryId = transaction.postings.find((posting) => posting.category_id)?.category_id
  return categories.find((category) => category.id === categoryId)
}
