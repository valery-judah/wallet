import { type FormEvent, useId, useState } from "react"
import {
  AccountFieldGrid,
  AccountFieldStack,
} from "@/components/accounts/account-layout"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { parseMajorAmount } from "@/lib/money"

type WithdrawValues = {
  amount_minor: number
  currency: string
}

type WithdrawFormProps = {
  currency: string
  errorMessage?: string
  isPending: boolean
  onSubmit: (values: WithdrawValues) => Promise<void>
}

export function WithdrawForm({
  currency,
  errorMessage,
  isPending,
  onSubmit,
}: WithdrawFormProps) {
  const amountId = useId()
  const [amountInput, setAmountInput] = useState("")
  const [amountErrorMessage, setAmountErrorMessage] = useState<string>()
  const parsedAmount = parseMajorAmount(amountInput, currency)
  const currentAmountErrorMessage =
    amountErrorMessage ?? (amountInput.trim().length > 0 ? parsedAmount.error : undefined)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (parsedAmount.amountMinor === undefined) {
      setAmountErrorMessage(parsedAmount.error)
      return
    }

    await onSubmit({
      amount_minor: parsedAmount.amountMinor,
      currency,
    })

    setAmountInput("")
    setAmountErrorMessage(undefined)
  }

  return (
    <form className="grid gap-6" onSubmit={handleSubmit}>
      <AccountFieldGrid columns="two">
        <AccountFieldStack>
          <Label htmlFor={amountId}>Amount</Label>
          <Input
            aria-invalid={currentAmountErrorMessage ? true : undefined}
            id={amountId}
            inputMode="decimal"
            onChange={(event) => {
              setAmountInput(event.target.value)
              setAmountErrorMessage(undefined)
            }}
            placeholder="25 or 25.50"
            required
            type="text"
            value={amountInput}
          />
          <p
            className={
              currentAmountErrorMessage
                ? "min-h-5 text-sm text-destructive"
                : "min-h-5 text-sm text-muted-foreground"
            }
          >
            {currentAmountErrorMessage ?? "Enter an amount like 25 or 25.50."}
          </p>
        </AccountFieldStack>

        <AccountFieldStack>
          <Label>Currency</Label>
          <div className="flex h-10 items-center rounded-md border border-input bg-muted/30 px-3 text-sm font-medium">
            {currency}
          </div>
          <p className="min-h-5 text-sm text-muted-foreground">
            This withdrawal uses the account currency.
          </p>
        </AccountFieldStack>
      </AccountFieldGrid>

      {errorMessage ? (
        <p className="rounded-2xl border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {errorMessage}
        </p>
      ) : null}

      <div className="flex flex-col gap-4 border-t border-border/70 pt-5 md:flex-row md:items-center md:justify-between">
        <p className="max-w-sm text-sm text-muted-foreground">
          The number of decimals depends on the currency.
        </p>
        <Button className="md:self-end" disabled={isPending} type="submit">
          {isPending ? "Submitting..." : "Withdraw"}
        </Button>
      </div>
    </form>
  )
}
