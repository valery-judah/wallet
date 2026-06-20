import { type FormEvent, useId, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

type CreateCardValues = {
  name: string
  currency: string
  opened_on?: string
}

type CreateCardFormProps = {
  errorMessage?: string
  isPending: boolean
  onSubmit: (values: CreateCardValues) => Promise<void>
}

export function CreateCardForm({
  errorMessage,
  isPending,
  onSubmit,
}: CreateCardFormProps) {
  const nameId = useId()
  const currencyId = useId()
  const openedOnId = useId()
  const [name, setName] = useState("")
  const [currency, setCurrency] = useState("ARS")
  const [openedOn, setOpenedOn] = useState(new Date().toISOString().slice(0, 10))

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    await onSubmit({
      name,
      currency,
      opened_on: openedOn || undefined,
    })
  }

  return (
    <form className="surface rounded-[2rem] p-8" onSubmit={handleSubmit}>
      <div className="grid gap-6">
        <div className="grid gap-2">
          <Label htmlFor={nameId}>Card name</Label>
          <Input
            id={nameId}
            onChange={(event) => setName(event.target.value)}
            placeholder="Groceries, travel, emergency cash"
            required
            value={name}
          />
        </div>

        <div className="grid gap-2 md:grid-cols-2 md:gap-4">
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
            <Label htmlFor={openedOnId}>Opening date</Label>
            <Input
              id={openedOnId}
              onChange={(event) => setOpenedOn(event.target.value)}
              type="date"
              value={openedOn}
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
            New cards start at zero balance.
          </p>
          <Button disabled={isPending} type="submit">
            {isPending ? "Creating..." : "Create card"}
          </Button>
        </div>
      </div>
    </form>
  )
}
