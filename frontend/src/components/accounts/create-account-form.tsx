import { type FormEvent, useId, useState } from "react"
import {
  ACCOUNT_COLOR_OPTIONS,
  ACCOUNT_TYPE_OPTIONS,
  AccountIcon,
  getAccountColorTheme,
  getAccountTypeLabel,
  type AccountColorKey,
  type AccountIconKey,
  type AccountTypeValue,
} from "@/components/accounts/account-appearance"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"

type CreateAccountValues = {
  name: string
  type: AccountTypeValue
  currency: string
  current_balance_minor: number
  opened_on?: string
  color_key?: string
  icon_key?: string
}

type CreateAccountFormProps = {
  errorMessage?: string
  isPending: boolean
  onSubmit: (values: CreateAccountValues) => Promise<void>
}

export function CreateAccountForm({
  errorMessage,
  isPending,
  onSubmit,
}: CreateAccountFormProps) {
  const nameId = useId()
  const typeId = useId()
  const currencyId = useId()
  const balanceId = useId()
  const openedOnId = useId()
  const iconId = useId()
  const [name, setName] = useState("")
  const [type, setType] = useState<AccountTypeValue>("card")
  const [currency, setCurrency] = useState("ARS")
  const [currentBalanceMinor, setCurrentBalanceMinor] = useState("0")
  const [openedOn, setOpenedOn] = useState(new Date().toISOString().slice(0, 10))
  const [colorKey, setColorKey] = useState<AccountColorKey | undefined>(undefined)
  const [iconKey, setIconKey] = useState<AccountIconKey | "">("")
  const theme = getAccountColorTheme(type, colorKey)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    await onSubmit({
      name,
      type,
      currency,
      current_balance_minor: Number(currentBalanceMinor),
      opened_on: openedOn || undefined,
      color_key: colorKey,
      icon_key: iconKey || undefined,
    })
  }

  return (
    <form className="surface rounded-[2rem] p-8" onSubmit={handleSubmit}>
      <div className="grid gap-6">
        <div className="grid gap-2">
          <Label htmlFor={nameId}>Account name</Label>
          <Input
            id={nameId}
            onChange={(event) => setName(event.target.value)}
            placeholder="Main card, cash wallet, reserve fund"
            required
            value={name}
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor={typeId}>Account type</Label>
          <select
            className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
            id={typeId}
            onChange={(event) => setType(event.target.value as AccountTypeValue)}
            value={type}
          >
            {ACCOUNT_TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="grid gap-2">
            <Label htmlFor={currencyId}>Currency</Label>
            <Input
              id={currencyId}
              maxLength={3}
              onChange={(event) => setCurrency(event.target.value.toUpperCase())}
              required
              value={currency}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor={balanceId}>Initial balance (minor units)</Label>
            <Input
              id={balanceId}
              inputMode="numeric"
              min="0"
              onChange={(event) => setCurrentBalanceMinor(event.target.value)}
              required
              type="number"
              value={currentBalanceMinor}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor={openedOnId}>Opening date</Label>
            <Input
              id={openedOnId}
              onChange={(event) => setOpenedOn(event.target.value)}
              type="date"
              value={openedOn}
            />
          </div>
        </div>

        <div className="grid gap-2">
          <Label>Accent color</Label>
          <div className="flex flex-wrap gap-3">
            {ACCOUNT_COLOR_OPTIONS.map((option) => {
              const optionTheme = getAccountColorTheme(type, option.value)

              return (
                <button
                  className={cn(
                    "flex size-10 items-center justify-center rounded-full border transition",
                    optionTheme.borderClassName,
                    colorKey === option.value
                      ? "ring-2 ring-primary ring-offset-2 ring-offset-background"
                      : "opacity-80 hover:opacity-100",
                  )}
                  key={option.value}
                  onClick={() => setColorKey(option.value)}
                  type="button"
                >
                  <span
                    className={cn("size-5 rounded-full", optionTheme.dotClassName)}
                  />
                  <span className="sr-only">{option.label}</span>
                </button>
              )
            })}
          </div>
        </div>

        <div className="grid gap-2">
          <Label htmlFor={iconId}>Icon override</Label>
          <select
            className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
            id={iconId}
            onChange={(event) => setIconKey(event.target.value as AccountIconKey | "")}
            value={iconKey}
          >
            <option value="">Default by type</option>
            {ACCOUNT_TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div
          className={cn(
            "relative overflow-hidden rounded-[1.6rem] border bg-card px-5 py-5",
            theme.borderClassName,
          )}
        >
          <div
            className={cn(
              "absolute inset-x-0 top-0 h-16 bg-gradient-to-r",
              theme.previewGlowClassName,
            )}
          />
          <div className="relative flex items-start gap-4">
            <div
              className={cn(
                "flex size-12 shrink-0 items-center justify-center rounded-2xl",
                theme.iconWrapClassName,
              )}
            >
              <AccountIcon type={type} iconKey={iconKey || undefined} />
            </div>
            <div className="min-w-0">
              <p className="truncate text-base font-semibold">
                {name || "Account name"}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                {getAccountTypeLabel(type)} · {currency || "Currency"}
              </p>
            </div>
          </div>
        </div>

        {errorMessage ? (
          <p className="rounded-2xl border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {errorMessage}
          </p>
        ) : null}

        <div className="flex items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            Account type shapes the UI; balance stays single-source in MVP.
          </p>
          <Button disabled={isPending} type="submit">
            {isPending ? "Creating..." : "Create account"}
          </Button>
        </div>
      </div>
    </form>
  )
}
