import { type FormEvent, useId, useState } from "react"
import {
  type AccountColorKey,
  type AccountTypeValue,
} from "@/components/accounts/account-appearance"
import {
  AccountColorField,
  AccountPreviewCard,
  AccountTypeField,
  AccountTypeGuide,
} from "@/components/accounts/account-form-sections"
import {
  AccountFieldGrid,
  AccountFieldStack,
  AccountSectionStack,
  AccountSplitLayout,
} from "@/components/accounts/account-layout"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { formatMajorAmountInput, parseMajorAmount } from "@/lib/money"

type CreateAccountValues = {
  name: string
  type: AccountTypeValue
  currency: string
  current_balance_minor: number
  opened_on?: string
  color_key?: string
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
  const currencyId = useId()
  const balanceId = useId()
  const openedOnId = useId()
  const [name, setName] = useState("")
  const [type, setType] = useState<AccountTypeValue>("card")
  const [currency, setCurrency] = useState("ARS")
  const [currentBalanceInput, setCurrentBalanceInput] = useState(
    formatMajorAmountInput(0, "ARS"),
  )
  const [openedOn, setOpenedOn] = useState(new Date().toISOString().slice(0, 10))
  const [colorKey, setColorKey] = useState<AccountColorKey | undefined>(undefined)
  const [balanceErrorMessage, setBalanceErrorMessage] = useState<string>()
  const parsedCurrentBalance = parseMajorAmount(currentBalanceInput, currency, {
    allowZero: true,
  })
  const currentBalanceErrorMessage =
    balanceErrorMessage ??
    (currentBalanceInput.trim().length > 0 ? parsedCurrentBalance.error : undefined)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (parsedCurrentBalance.amountMinor === undefined) {
      setBalanceErrorMessage(parsedCurrentBalance.error)
      return
    }

    await onSubmit({
      name,
      type,
      currency,
      current_balance_minor: parsedCurrentBalance.amountMinor,
      opened_on: openedOn || undefined,
      color_key: colorKey,
    })
  }

  return (
    <AccountSplitLayout className="xl:grid-cols-[minmax(0,1.25fr)_320px]">
      <form
        className="rounded-[2rem] border border-border/70 bg-card/80 p-8 shadow-[0_24px_90px_-60px_rgba(15,23,42,0.45)]"
        onSubmit={handleSubmit}
      >
        <AccountSectionStack className="gap-7">
          <AccountFieldStack>
            <Label htmlFor={nameId}>Account name</Label>
            <Input
              id={nameId}
              onChange={(event) => setName(event.target.value)}
              placeholder="Main card, cash wallet, reserve fund"
              required
              value={name}
            />
          </AccountFieldStack>

          <AccountTypeField onChange={setType} type={type} />

          <section className="grid gap-4 rounded-[1.6rem] border border-border/70 bg-background/35 p-5">
            <div className="grid gap-1">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-muted-foreground">
                Account setup
              </p>
              <p className="text-sm text-muted-foreground">
                Set the currency, starting balance, and opening date for this
                account.
              </p>
            </div>

            <AccountFieldGrid columns="three">
              <AccountFieldStack>
                <Label htmlFor={currencyId}>Currency</Label>
                <Input
                  id={currencyId}
                  maxLength={3}
                  onChange={(event) => {
                    setCurrency(event.target.value.toUpperCase())
                    setBalanceErrorMessage(undefined)
                  }}
                  required
                  value={currency}
                />
                <p className="min-h-5 text-xs leading-5 text-muted-foreground">
                  ISO code like ARS or USD.
                </p>
              </AccountFieldStack>

              <AccountFieldStack>
                <Label htmlFor={balanceId}>Starting balance</Label>
                <Input
                  aria-invalid={currentBalanceErrorMessage ? true : undefined}
                  id={balanceId}
                  inputMode="decimal"
                  onChange={(event) => {
                    setCurrentBalanceInput(event.target.value)
                    setBalanceErrorMessage(undefined)
                  }}
                  placeholder="300 or 300.50"
                  required
                  type="text"
                  value={currentBalanceInput}
                />
                <p
                  className={
                    currentBalanceErrorMessage
                      ? "min-h-5 text-xs leading-5 text-destructive"
                      : "min-h-5 text-xs leading-5 text-muted-foreground"
                  }
                >
                  {currentBalanceErrorMessage ?? "Enter an amount like 300 or 300.50."}
                </p>
              </AccountFieldStack>

              <AccountFieldStack>
                <Label htmlFor={openedOnId}>Opening date</Label>
                <Input
                  id={openedOnId}
                  onChange={(event) => setOpenedOn(event.target.value)}
                  type="date"
                  value={openedOn}
                />
                <p className="min-h-5 text-xs leading-5 text-muted-foreground">
                  The starting date for this account.
                </p>
              </AccountFieldStack>
            </AccountFieldGrid>
          </section>

          <AccountColorField colorKey={colorKey} onChange={setColorKey} type={type} />

          <section className="grid gap-3 rounded-[1.6rem] border border-border/70 bg-background/35 p-5">
            <div className="grid gap-1">
              <Label>Preview</Label>
              <p className="text-sm text-muted-foreground">
                Check how this account will appear before you create it.
              </p>
            </div>
            <AccountPreviewCard
              balanceMinor={parsedCurrentBalance.amountMinor}
              colorKey={colorKey}
              currency={currency}
              name={name}
              type={type}
            />
          </section>

          {errorMessage ? (
            <p className="rounded-2xl border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {errorMessage}
            </p>
          ) : null}

          <div className="flex items-center justify-between gap-4">
            <p className="max-w-xl text-sm text-muted-foreground">
              The account type helps organize and recognize this account across
              the app.
            </p>
            <Button disabled={isPending} type="submit">
              {isPending ? "Creating..." : "Create account"}
            </Button>
          </div>
        </AccountSectionStack>
      </form>

      <AccountTypeGuide />
    </AccountSplitLayout>
  )
}
