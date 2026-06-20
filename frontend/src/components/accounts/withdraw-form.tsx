import { type FormEvent, useEffect, useId, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

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
  const currencyId = useId()
  const [amountMinor, setAmountMinor] = useState("")
  const [formCurrency, setFormCurrency] = useState(currency)

  useEffect(() => {
    setFormCurrency(currency)
  }, [currency])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    await onSubmit({
      amount_minor: Number(amountMinor),
      currency: formCurrency,
    })

    setAmountMinor("")
  }

  return (
    <form className="surface rounded-[2rem] p-8" onSubmit={handleSubmit}>
      <div className="grid gap-6">
        <div>
          <h2 className="text-xl font-semibold">Withdraw money</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Use the account currency and submit the amount in minor units.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor={amountId}>Amount in minor units</Label>
            <Input
              id={amountId}
              inputMode="numeric"
              min="1"
              onChange={(event) => setAmountMinor(event.target.value)}
              placeholder="1250"
              required
              type="number"
              value={amountMinor}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor={currencyId}>Currency</Label>
            <Input
              id={currencyId}
              maxLength={3}
              onChange={(event) =>
                setFormCurrency(event.target.value.toUpperCase())
              }
              required
              value={formCurrency}
            />
          </div>
        </div>

        {errorMessage ? (
          <p className="rounded-2xl border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {errorMessage}
          </p>
        ) : null}

        <div className="flex items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            Example: `1250` means 12.50 units for two-decimal currencies.
          </p>
          <Button disabled={isPending} type="submit">
            {isPending ? "Submitting..." : "Withdraw"}
          </Button>
        </div>
      </div>
    </form>
  )
}
