import { type FormEvent, useId, useState } from "react"
import type { AccountResponse } from "@/client"
import {
  type AccountColorKey,
  type AccountTypeValue,
} from "@/components/accounts/account-appearance"
import {
  AccountColorField,
  AccountPreviewCard,
  AccountTypeField,
} from "@/components/accounts/account-form-sections"
import {
  AccountFieldStack,
  AccountSectionStack,
} from "@/components/accounts/account-layout"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

type UpdateAccountProfileValues = {
  name: string
  type: AccountTypeValue
  color_key?: string
}

type AccountProfileFormProps = {
  account: AccountResponse
  errorMessage?: string
  isPending: boolean
  onSubmit: (values: UpdateAccountProfileValues) => Promise<void>
}

export function AccountProfileForm({
  account,
  errorMessage,
  isPending,
  onSubmit,
}: AccountProfileFormProps) {
  const nameId = useId()
  const [name, setName] = useState(account.name)
  const [type, setType] = useState<AccountTypeValue>(account.type)
  const [colorKey, setColorKey] = useState<AccountColorKey | undefined>(
    (account.color_key as AccountColorKey | null) ?? undefined,
  )

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    await onSubmit({
      name,
      type,
      color_key: colorKey,
    })
  }

  return (
    <form className="grid gap-6" onSubmit={handleSubmit}>
      <AccountSectionStack>
        <AccountFieldStack>
          <Label htmlFor={nameId}>Account name</Label>
          <Input
            id={nameId}
            onChange={(event) => setName(event.target.value)}
            required
            value={name}
          />
        </AccountFieldStack>

        <AccountTypeField onChange={setType} type={type} />

        <AccountColorField colorKey={colorKey} onChange={setColorKey} type={type} />

        <div className="grid gap-3">
          <Label>Preview</Label>
          <AccountPreviewCard
            balanceMinor={account.current_balance.amount_minor}
            colorKey={colorKey}
            currency={account.currency}
            name={name}
            statusLabel={account.status}
            type={type}
          />
        </div>
      </AccountSectionStack>

      {errorMessage ? (
        <p className="rounded-2xl border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {errorMessage}
        </p>
      ) : null}

      <div className="flex justify-end">
        <Button disabled={isPending} type="submit">
          {isPending ? "Saving..." : "Save profile"}
        </Button>
      </div>
    </form>
  )
}
