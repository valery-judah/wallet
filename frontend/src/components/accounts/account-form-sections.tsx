import {
  ACCOUNT_COLOR_OPTIONS,
  ACCOUNT_TYPE_OPTIONS,
  AccountIcon,
  getAccountColorTheme,
  getAccountTypeLabel,
  type AccountColorKey,
  type AccountTypeValue,
} from "@/components/accounts/account-appearance"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { formatMoney } from "@/lib/format"
import { cn } from "@/lib/utils"

export function AccountTypeField({
  type,
  onChange,
}: {
  type: AccountTypeValue
  onChange: (value: AccountTypeValue) => void
}) {
  return (
    <section className="grid gap-4 rounded-[1.6rem] border border-border/70 bg-background/35 p-5">
      <div className="grid gap-1">
        <Label>Account type</Label>
        <p className="text-sm text-muted-foreground">
          Choose the bucket first. Type drives iconography, defaults, and grouping.
        </p>
      </div>
      <div
        aria-label="Account type"
        className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3"
        role="radiogroup"
      >
        {ACCOUNT_TYPE_OPTIONS.map((option) => {
          const selected = option.value === type
          const theme = getAccountColorTheme(option.value, selected ? option.defaultColorKey : null)

          return (
            <button
              aria-pressed={selected}
              aria-checked={selected}
              className={cn(
                "h-full rounded-[1.4rem] border p-4 text-left transition",
                selected
                  ? cn(
                      theme.borderClassName,
                      "bg-card shadow-[0_20px_50px_-32px_rgba(0,0,0,0.55)]",
                    )
                  : "border-border/70 bg-background/70 hover:border-border hover:bg-accent/40",
              )}
              key={option.value}
              onClick={() => onChange(option.value)}
              role="radio"
              type="button"
            >
              <div className="flex h-full items-start gap-3">
                <div
                  className={cn(
                    "flex size-11 shrink-0 items-center justify-center rounded-2xl",
                    selected
                      ? theme.iconWrapClassName
                      : "bg-muted text-muted-foreground ring-1 ring-border/60",
                  )}
                >
                  <AccountIcon type={option.value} />
                </div>
                <div className="min-w-0">
                  <p className="leading-tight font-semibold">{option.label}</p>
                  <p className="mt-1 text-sm leading-5 text-muted-foreground">
                    {option.description}
                  </p>
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </section>
  )
}

export function AccountColorField({
  type,
  colorKey,
  onChange,
}: {
  type: AccountTypeValue
  colorKey?: AccountColorKey
  onChange: (value: AccountColorKey | undefined) => void
}) {
  return (
    <section className="grid gap-4 rounded-[1.6rem] border border-border/70 bg-background/35 p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="grid gap-1">
          <Label>Accent color</Label>
          <p className="text-sm text-muted-foreground">
            Keep the type default or override it with a custom accent.
          </p>
        </div>
        <Button
          className="md:self-start"
          onClick={() => onChange(undefined)}
          size="sm"
          type="button"
          variant={colorKey ? "outline" : "secondary"}
        >
          {colorKey ? "Use type default" : "Using type default"}
        </Button>
      </div>
      <div className="flex flex-wrap gap-3">
        {ACCOUNT_COLOR_OPTIONS.map((option) => {
          const optionTheme = getAccountColorTheme(type, option.value)

          return (
            <button
              aria-pressed={colorKey === option.value}
              className={cn(
                "flex size-10 items-center justify-center rounded-full border transition",
                optionTheme.borderClassName,
                colorKey === option.value
                  ? "ring-2 ring-primary ring-offset-2 ring-offset-background"
                  : "opacity-80 hover:opacity-100",
              )}
              key={option.value}
              onClick={() => onChange(option.value)}
              type="button"
            >
              <span className={cn("size-5 rounded-full", optionTheme.dotClassName)} />
              <span className="sr-only">{option.label}</span>
            </button>
          )
        })}
      </div>
    </section>
  )
}

export function AccountPreviewCard({
  name,
  type,
  currency,
  colorKey,
  balanceMinor,
  statusLabel,
}: {
  name: string
  type: AccountTypeValue
  currency: string
  colorKey?: AccountColorKey
  balanceMinor?: number
  statusLabel?: string
}) {
  const theme = getAccountColorTheme(type, colorKey)

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[1.6rem] border bg-card px-5 py-5",
        theme.borderClassName,
      )}
    >
      <div
        className={cn(
          "absolute inset-0 bg-gradient-to-br",
          theme.previewGlowClassName,
        )}
      />
      <div className="relative flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-4">
          <div
            className={cn(
              "flex size-12 shrink-0 items-center justify-center rounded-2xl",
              theme.iconWrapClassName,
            )}
          >
            <AccountIcon type={type} />
          </div>
          <div className="min-w-0">
            <p className="truncate text-base font-semibold">{name || "Account name"}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {getAccountTypeLabel(type)} · {currency || "Currency"}
            </p>
          </div>
        </div>
        {statusLabel ? (
          <span className="rounded-full bg-muted px-3 py-1 text-xs font-semibold text-muted-foreground">
            {statusLabel}
          </span>
        ) : null}
      </div>
      {typeof balanceMinor === "number" && Number.isFinite(balanceMinor) ? (
        <p className="relative mt-6 text-2xl font-semibold">
          {formatMoney(balanceMinor, currency || "ARS")}
        </p>
      ) : null}
    </div>
  )
}

export function AccountTypeGuide() {
  return (
    <aside className="grid gap-5">
      <section className="rounded-[1.8rem] border border-border/70 bg-card/70 p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-muted-foreground">
          Account types
        </p>
        <div className="mt-5 grid gap-4">
          {ACCOUNT_TYPE_OPTIONS.map((option) => (
            <div className="flex items-start gap-3" key={option.value}>
              <div
                className={cn(
                  "flex size-10 shrink-0 items-center justify-center rounded-2xl",
                  getAccountColorTheme(option.value, option.defaultColorKey).iconWrapClassName,
                )}
              >
                <AccountIcon type={option.value} />
              </div>
              <div>
                <p className="font-medium">{option.label}</p>
                <p className="mt-1 text-sm leading-5 text-muted-foreground">
                  {option.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-[1.8rem] border border-border/70 bg-card/70 p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-muted-foreground">
          Tips
        </p>
        <div className="mt-4 grid gap-3 text-sm leading-6 text-muted-foreground">
          <p>Each account uses one currency.</p>
          <p>Closed accounts stay in your list with their final balance.</p>
          <p>Choose the type that best matches where this money lives.</p>
        </div>
      </section>
    </aside>
  )
}
