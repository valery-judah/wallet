import { type FormEvent, useId, useMemo, useState } from "react"
import type {
  AccountResponse,
  CreateTransactionRequest,
  IncomeCategoryResponse,
  SpendingCategoryResponse,
} from "@/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { formatMoney } from "@/lib/format"
import { parseMajorAmount } from "@/lib/money"
import type { CategoryTreeNode } from "@/lib/categories"

type TransactionComposerProps = {
  account: AccountResponse
  accounts: Array<AccountResponse>
  incomeCategories: Array<IncomeCategoryResponse>
  spendingCategories: Array<SpendingCategoryResponse>
  errorMessage?: string
  isPending: boolean
  onSubmit: (payload: CreateTransactionRequest) => Promise<void>
}

type ComposerType = "expense" | "income" | "transfer" | "adjustment"

type FlatCategory = {
  id: string
  label: string
}

type ExpenseSplitDraft = {
  id: string
  categoryId: string
  amountInput: string
}

export function TransactionComposer({
  account,
  accounts,
  incomeCategories: incomeCategoryTree,
  spendingCategories,
  errorMessage,
  isPending,
  onSubmit,
}: TransactionComposerProps) {
  const amountId = useId()
  const descriptionId = useId()
  const occurredOnId = useId()
  const categoryId = useId()
  const transferId = useId()
  const notesId = useId()
  const [type, setType] = useState<ComposerType>("expense")
  const [amountInput, setAmountInput] = useState("")
  const [description, setDescription] = useState("")
  const [occurredOn, setOccurredOn] = useState(new Date().toISOString().slice(0, 10))
  const [selectedCategoryId, setSelectedCategoryId] = useState("")
  const [transferAccountId, setTransferAccountId] = useState("")
  const [expenseSplits, setExpenseSplits] = useState<Array<ExpenseSplitDraft>>([
    createExpenseSplitDraft(),
  ])
  const [adjustmentDirection, setAdjustmentDirection] = useState<"increase" | "decrease">(
    "increase",
  )
  const [notes, setNotes] = useState("")
  const [formErrorMessage, setFormErrorMessage] = useState<string>()

  const expenseCategories = useMemo(
    () => flattenCategories(spendingCategories),
    [spendingCategories],
  )
  const incomeCategoryOptions = useMemo(
    () => flattenCategories(incomeCategoryTree),
    [incomeCategoryTree],
  )
  const transferAccounts = useMemo(
    () =>
      accounts.filter(
        (candidate) =>
          candidate.id !== account.id &&
          candidate.archived_at === null &&
          candidate.currency === account.currency,
      ),
    [account.currency, account.id, accounts],
  )
  const parsedAmount = parseMajorAmount(amountInput, account.currency)
  const availableCategories = type === "expense" ? expenseCategories : incomeCategoryOptions
  const parsedExpenseTotal = useMemo(() => {
    if (type !== "expense") {
      return undefined
    }

    let total = 0
    for (const split of expenseSplits) {
      const parsedSplit = parseMajorAmount(split.amountInput, account.currency)
      if (parsedSplit.amountMinor === undefined) {
        return undefined
      }
      total += parsedSplit.amountMinor
    }
    return total
  }, [account.currency, expenseSplits, type])
  const activeErrorMessage =
    formErrorMessage ??
    (type !== "expense" && amountInput.trim().length > 0 ? parsedAmount.error : undefined) ??
    errorMessage

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormErrorMessage(undefined)

    let payload: CreateTransactionRequest | undefined

    if (type === "expense") {
      if (expenseCategories.length === 0) {
        setFormErrorMessage("No expense categories are available yet.")
        return
      }

      const categoryPostings: CreateTransactionRequest["postings"] = []
      let totalAmountMinor = 0

      for (const [index, split] of expenseSplits.entries()) {
        const fallbackCategoryId = split.categoryId || expenseCategories[0]?.id
        if (!fallbackCategoryId) {
          setFormErrorMessage(`Split ${index + 1}: choose a spending category.`)
          return
        }

        const parsedSplit = parseMajorAmount(split.amountInput, account.currency)
        if (parsedSplit.amountMinor === undefined) {
          setFormErrorMessage(`Split ${index + 1}: ${parsedSplit.error}`)
          return
        }

        totalAmountMinor += parsedSplit.amountMinor
        categoryPostings.push({
          category_id: fallbackCategoryId,
          amount_minor: parsedSplit.amountMinor,
          currency: account.currency,
        })
      }

      payload = {
        type,
        description: description || undefined,
        occurred_on: occurredOn || undefined,
        notes: notes || undefined,
        postings: [
          {
            account_id: account.id,
            amount_minor: -totalAmountMinor,
            currency: account.currency,
          },
          ...categoryPostings,
        ],
      }
    }

    if (type === "income") {
      if (parsedAmount.amountMinor === undefined) {
        setFormErrorMessage(parsedAmount.error)
        return
      }

      const amountMinor = parsedAmount.amountMinor
      const fallbackCategoryId = selectedCategoryId || availableCategories[0]?.id
      if (!fallbackCategoryId) {
        setFormErrorMessage(`No ${type} categories are available yet.`)
        return
      }
      payload = {
        type,
        description: description || undefined,
        occurred_on: occurredOn || undefined,
        notes: notes || undefined,
        postings: [
              { account_id: account.id, amount_minor: amountMinor, currency: account.currency },
              {
                category_id: fallbackCategoryId,
                amount_minor: -amountMinor,
                currency: account.currency,
              },
        ],
      }
    }

    if (type === "transfer") {
      if (parsedAmount.amountMinor === undefined) {
        setFormErrorMessage(parsedAmount.error)
        return
      }

      const amountMinor = parsedAmount.amountMinor
      const fallbackAccountId = transferAccountId || transferAccounts[0]?.id
      if (!fallbackAccountId) {
        setFormErrorMessage(
          `Create another active ${account.currency} account before recording a transfer.`,
        )
        return
      }
      payload = {
        type,
        description: description || undefined,
        occurred_on: occurredOn || undefined,
        notes: notes || undefined,
        postings: [
          {
            account_id: account.id,
            amount_minor: -amountMinor,
            currency: account.currency,
          },
          {
            account_id: fallbackAccountId,
            amount_minor: amountMinor,
            currency: account.currency,
          },
        ],
      }
    }

    if (type === "adjustment") {
      if (parsedAmount.amountMinor === undefined) {
        setFormErrorMessage(parsedAmount.error)
        return
      }

      const amountMinor = parsedAmount.amountMinor
      payload = {
        type,
        description: description || undefined,
        occurred_on: occurredOn || undefined,
        notes: notes || undefined,
        postings: [
          {
            account_id: account.id,
            amount_minor:
              adjustmentDirection === "increase" ? amountMinor : -amountMinor,
            currency: account.currency,
          },
        ],
      }
    }

    if (!payload) {
      setFormErrorMessage("Choose a transaction type.")
      return
    }

    await onSubmit(payload)
  }

  return (
    <form className="grid gap-5" onSubmit={handleSubmit}>
      <div className="grid gap-2">
        <Label>Transaction type</Label>
        <div className="grid gap-2 sm:grid-cols-2">
          {(
            [
              ["expense", "Expense"],
              ["income", "Income"],
              ["transfer", "Transfer"],
              ["adjustment", "Adjustment"],
            ] as const
          ).map(([value, label]) => (
            <button
              aria-pressed={type === value}
              className={
                type === value
                  ? "rounded-2xl border border-primary/50 bg-primary/10 px-4 py-3 text-left text-sm font-semibold"
                  : "rounded-2xl border border-border/70 bg-background/70 px-4 py-3 text-left text-sm font-semibold"
              }
              key={value}
              onClick={() => setType(value)}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {type !== "expense" ? (
          <div className="grid gap-2">
            <Label htmlFor={amountId}>Amount</Label>
            <Input
              id={amountId}
              inputMode="decimal"
              onChange={(event) => {
                setAmountInput(event.target.value)
                setFormErrorMessage(undefined)
              }}
              placeholder="25 or 25.50"
              value={amountInput}
            />
          </div>
        ) : (
          <div className="grid gap-2">
            <Label>Split total</Label>
            <div className="flex h-11 items-center rounded-md border border-input bg-muted/20 px-3 text-sm font-medium">
              {parsedExpenseTotal === undefined
                ? "Enter split amounts"
                : formatMoney(parsedExpenseTotal, account.currency)}
            </div>
          </div>
        )}
        <div className="grid gap-2">
          <Label htmlFor={occurredOnId}>Date</Label>
          <Input
            id={occurredOnId}
            onChange={(event) => setOccurredOn(event.target.value)}
            type="date"
            value={occurredOn}
          />
        </div>
      </div>

      <div className="grid gap-2">
        <Label htmlFor={descriptionId}>Description</Label>
        <Input
          id={descriptionId}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Lunch, salary, transfer to savings"
          value={description}
        />
      </div>

      {type === "expense" && expenseCategories.length > 0 ? (
        <div className="grid gap-3">
          <div className="flex items-center justify-between gap-3">
            <Label>Expense splits</Label>
            <Button
              onClick={() =>
                setExpenseSplits((current) => [...current, createExpenseSplitDraft()])
              }
              type="button"
              variant="outline"
            >
              Add split
            </Button>
          </div>
          <div className="grid gap-3">
            {expenseSplits.map((split) => (
              <div
                className="grid items-end gap-3 rounded-2xl border border-border/70 bg-background/70 p-3 md:grid-cols-[minmax(0,1fr)_minmax(8rem,10rem)_auto]"
                key={split.id}
              >
                <div className="grid min-w-0 gap-2">
                  <Label htmlFor={`${categoryId}-${split.id}`}>Expense category</Label>
                  <select
                    className="h-11 w-full min-w-0 rounded-md border border-input bg-transparent px-3 text-sm"
                    id={`${categoryId}-${split.id}`}
                    onChange={(event) => {
                      setExpenseSplits((current) =>
                        current.map((entry) =>
                          entry.id === split.id
                            ? { ...entry, categoryId: event.target.value }
                            : entry,
                        ),
                      )
                      setFormErrorMessage(undefined)
                    }}
                    value={split.categoryId}
                  >
                    <option value="">Use {expenseCategories[0]?.label ?? "a category"}</option>
                    {expenseCategories.map((category) => (
                      <option key={category.id} value={category.id}>
                        {category.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid min-w-0 gap-2">
                  <Label htmlFor={`${amountId}-${split.id}`}>Split amount</Label>
                  <Input
                    className="w-full min-w-0"
                    id={`${amountId}-${split.id}`}
                    inputMode="decimal"
                    onChange={(event) => {
                      setExpenseSplits((current) =>
                        current.map((entry) =>
                          entry.id === split.id
                            ? { ...entry, amountInput: event.target.value }
                            : entry,
                        ),
                      )
                      setFormErrorMessage(undefined)
                    }}
                    placeholder="0.00"
                    value={split.amountInput}
                  />
                </div>
                <div className="flex items-end md:justify-self-end">
                  <Button
                    disabled={expenseSplits.length === 1}
                    onClick={() =>
                      setExpenseSplits((current) =>
                        current.length === 1
                          ? current
                          : current.filter((entry) => entry.id !== split.id),
                      )
                    }
                    type="button"
                    variant="ghost"
                  >
                    Remove
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {type === "income" && availableCategories.length > 0 ? (
        <div className="grid gap-2">
          <Label htmlFor={categoryId}>Income category</Label>
          <select
            className="h-11 rounded-md border border-input bg-transparent px-3 text-sm"
            id={categoryId}
            onChange={(event) => setSelectedCategoryId(event.target.value)}
            value={selectedCategoryId}
          >
            <option value="">Use {availableCategories[0]?.label ?? "a category"}</option>
            {availableCategories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.label}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      {type === "transfer" ? (
        <div className="grid gap-2">
          <Label htmlFor={transferId}>Destination account</Label>
          <select
            className="h-11 rounded-md border border-input bg-transparent px-3 text-sm"
            id={transferId}
            onChange={(event) => setTransferAccountId(event.target.value)}
            value={transferAccountId}
          >
            <option value="">Choose an account</option>
            {transferAccounts.map((candidate) => (
              <option key={candidate.id} value={candidate.id}>
                {candidate.name} · {candidate.currency}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      {type === "adjustment" ? (
        <div className="grid gap-2">
          <Label>Direction</Label>
          <div className="grid gap-2 sm:grid-cols-2">
            <button
              aria-pressed={adjustmentDirection === "increase"}
              className={
                adjustmentDirection === "increase"
                  ? "rounded-2xl border border-primary/50 bg-primary/10 px-4 py-3 text-left text-sm font-semibold"
                  : "rounded-2xl border border-border/70 bg-background/70 px-4 py-3 text-left text-sm font-semibold"
              }
              onClick={() => setAdjustmentDirection("increase")}
              type="button"
            >
              Increase balance
            </button>
            <button
              aria-pressed={adjustmentDirection === "decrease"}
              className={
                adjustmentDirection === "decrease"
                  ? "rounded-2xl border border-primary/50 bg-primary/10 px-4 py-3 text-left text-sm font-semibold"
                  : "rounded-2xl border border-border/70 bg-background/70 px-4 py-3 text-left text-sm font-semibold"
              }
              onClick={() => setAdjustmentDirection("decrease")}
              type="button"
            >
              Decrease balance
            </button>
          </div>
        </div>
      ) : null}

      <div className="grid gap-2">
        <Label htmlFor={notesId}>Notes</Label>
        <Input
          id={notesId}
          onChange={(event) => setNotes(event.target.value)}
          placeholder="Optional context"
          value={notes}
        />
      </div>

      {activeErrorMessage ? (
        <p className="rounded-2xl border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {activeErrorMessage}
        </p>
      ) : null}

      <div className="flex justify-end">
        <Button disabled={isPending} type="submit">
          {isPending ? "Saving..." : "Record transaction"}
        </Button>
      </div>
    </form>
  )
}

function flattenCategories(
  categories: Array<CategoryTreeNode>,
): Array<FlatCategory> {
  return categories
    .flatMap((category) => {
      const children = category.children ?? []
      if (children.length === 0) {
        return [{ id: category.id, label: category.name }]
      }

      return children.map((child) => ({
        id: child.id,
        label: `${category.name} / ${child.name}`,
      }))
    })
}

function createExpenseSplitDraft(): ExpenseSplitDraft {
  return {
    id: `expense-split-${Math.random().toString(36).slice(2, 10)}`,
    categoryId: "",
    amountInput: "",
  }
}
