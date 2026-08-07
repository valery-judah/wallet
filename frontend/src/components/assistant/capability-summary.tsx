import type { TaskViewResponse } from "@/client"
import { formatMoney } from "@/lib/format"

type UnknownRecord = Record<string, unknown>
type BalanceRow = UnknownRecord & {
  name: string
  currency: string
  balance_minor: number
}
type TotalRow = UnknownRecord & {
  currency: string
  balance_minor: number
}

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function readableField(field: string): string {
  return field
    .replaceAll("_id", "")
    .replaceAll("_minor", " (minor)")
    .replaceAll("_", " ")
    .replace(/^./, (character) => character.toUpperCase())
}

function readableValue(value: unknown): string {
  if (typeof value === "string" || typeof value === "number") {
    return String(value)
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No"
  }
  return JSON.stringify(value)
}

function TransactionCaptureSummary({ data }: { data: UnknownRecord }) {
  const phase = data.phase
  const candidate = data.candidate
  const interaction = data.interaction
  if (typeof phase !== "string" || !isRecord(candidate)) {
    return null
  }

  const populatedFields = Object.entries(candidate).filter(([, value]) => value !== null)
  const options =
    isRecord(interaction) && Array.isArray(interaction.options)
      ? interaction.options.filter(
          (option): option is { label: string; value: string } =>
            isRecord(option) &&
            typeof option.label === "string" &&
            typeof option.value === "string",
        )
      : []

  return (
    <section className="mt-3 rounded-xl border bg-background/70 p-4" aria-label="Transaction draft">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold">Transaction draft</p>
        <span className="rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground">
          {phase.replaceAll("_", " ")}
        </span>
      </div>
      {populatedFields.length > 0 ? (
        <dl className="mt-3 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
          {populatedFields.map(([field, value]) => (
            <div key={field} className="grid grid-cols-[minmax(7rem,auto)_1fr] gap-2">
              <dt className="text-muted-foreground">{readableField(field)}</dt>
              <dd className="min-w-0 break-words font-medium">{readableValue(value)}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="mt-3 text-sm text-muted-foreground">No transaction details collected yet.</p>
      )}
      {options.length > 0 && (
        <div className="mt-4 border-t pt-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Available choices
          </p>
          <ul className="mt-2 flex flex-wrap gap-2">
            {options.map((option) => (
              <li key={option.value} className="rounded-full border bg-card px-3 py-1.5 text-sm">
                {option.label}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

function WalletStateSummary({ data }: { data: UnknownRecord }) {
  if (!Array.isArray(data.accounts) || !Array.isArray(data.totals_by_currency)) {
    return null
  }
  const accounts = data.accounts.filter(
    (account): account is BalanceRow =>
      isRecord(account) &&
      typeof account.name === "string" &&
      typeof account.currency === "string" &&
      typeof account.balance_minor === "number",
  )
  const totals = data.totals_by_currency.filter(
    (total): total is TotalRow =>
      isRecord(total) &&
      typeof total.currency === "string" &&
      typeof total.balance_minor === "number",
  )
  if (accounts.length !== data.accounts.length || totals.length !== data.totals_by_currency.length) {
    return null
  }

  return (
    <section className="mt-3 rounded-xl border bg-background/70 p-4" aria-label="Wallet balances">
      <p className="text-sm font-semibold">Wallet balances</p>
      {accounts.length > 0 ? (
        <ul className="mt-3 grid gap-2 sm:grid-cols-2">
          {accounts.map((account) => (
            <li
              key={`${String(account.id)}-${account.name}`}
              className="flex items-center justify-between gap-3 rounded-lg bg-muted/60 px-3 py-2 text-sm"
            >
              <span className="truncate">{account.name}</span>
              <span className="font-semibold">
                {formatMoney(account.balance_minor, account.currency)}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-muted-foreground">No active accounts.</p>
      )}
      {totals.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2 border-t pt-3">
          {totals.map((total) => (
            <span key={String(total.currency)} className="rounded-full bg-primary/10 px-3 py-1 text-sm">
              Total {formatMoney(total.balance_minor, total.currency)}
            </span>
          ))}
        </div>
      )}
    </section>
  )
}

export function CapabilitySummary({ view }: { view: TaskViewResponse }) {
  if (view.kind === "transaction_capture") {
    return <TransactionCaptureSummary data={view.data} />
  }
  if (view.kind === "wallet_state") {
    return <WalletStateSummary data={view.data} />
  }
  return null
}
