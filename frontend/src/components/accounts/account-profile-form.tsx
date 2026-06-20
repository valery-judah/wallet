import { type FormEvent, useId, useState } from "react"
import type { AccountResponse } from "@/client"
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

type UpdateAccountProfileValues = {
  name: string
  type: AccountTypeValue
  color_key?: string
  icon_key?: string
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
  const typeId = useId()
  const iconId = useId()
  const [name, setName] = useState(account.name)
  const [type, setType] = useState<AccountTypeValue>(account.type)
  const [colorKey, setColorKey] = useState<AccountColorKey | undefined>(
    (account.color_key as AccountColorKey | null) ?? undefined,
  )
  const [iconKey, setIconKey] = useState<AccountIconKey | "">(
    (account.icon_key as AccountIconKey | null) ?? "",
  )
  const theme = getAccountColorTheme(type, colorKey)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    await onSubmit({
      name,
      type,
      color_key: colorKey,
      icon_key: iconKey || undefined,
    })
  }

  return (
    <form className="grid gap-6" onSubmit={handleSubmit}>
      <div className="grid gap-2">
        <Label htmlFor={nameId}>Account name</Label>
        <Input
          id={nameId}
          onChange={(event) => setName(event.target.value)}
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
                <span className={cn("size-5 rounded-full", optionTheme.dotClassName)} />
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
            <p className="truncate text-base font-semibold">{name || "Account name"}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {getAccountTypeLabel(type)}
            </p>
          </div>
        </div>
      </div>

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
