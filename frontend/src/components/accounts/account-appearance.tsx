import type { ComponentType } from "react"
import {
  Banknote,
  Briefcase,
  CircleHelp,
  CreditCard,
  Landmark,
  PiggyBank,
  Wallet,
} from "lucide-react"
import { cn } from "@/lib/utils"

export type AccountTypeValue =
  | "card"
  | "cash"
  | "bank"
  | "wallet"
  | "platform"
  | "savings"
  | "other"

export type AccountIconKey = AccountTypeValue

export type AccountColorKey =
  | "violet"
  | "emerald"
  | "blue"
  | "cyan"
  | "amber"
  | "rose"
  | "slate"

type AccountPresentation = {
  value: AccountTypeValue
  label: string
  description: string
  defaultColorKey: AccountColorKey
  defaultIconKey: AccountIconKey
}

type AccountColorTheme = {
  badgeClassName: string
  borderClassName: string
  dotClassName: string
  iconWrapClassName: string
  previewGlowClassName: string
}

export const ACCOUNT_TYPE_OPTIONS: Array<AccountPresentation> = [
  {
    value: "card",
    label: "Card",
    description: "Debit, credit, and prepaid cards.",
    defaultColorKey: "violet",
    defaultIconKey: "card",
  },
  {
    value: "cash",
    label: "Cash",
    description: "Physical cash, wallets, and pocket money.",
    defaultColorKey: "emerald",
    defaultIconKey: "cash",
  },
  {
    value: "bank",
    label: "Bank account",
    description: "Checking, current, and standard bank balances.",
    defaultColorKey: "blue",
    defaultIconKey: "bank",
  },
  {
    value: "wallet",
    label: "Digital wallet",
    description: "Wallet apps like Mercado Pago, PayPal, or Wise.",
    defaultColorKey: "cyan",
    defaultIconKey: "wallet",
  },
  {
    value: "platform",
    label: "Money platform",
    description: "Platforms like Payoneer or payout balances.",
    defaultColorKey: "amber",
    defaultIconKey: "platform",
  },
  {
    value: "savings",
    label: "Savings",
    description: "Reserve funds and dedicated savings balances.",
    defaultColorKey: "rose",
    defaultIconKey: "savings",
  },
  {
    value: "other",
    label: "Other",
    description: "Anything that does not fit the standard account set.",
    defaultColorKey: "slate",
    defaultIconKey: "other",
  },
]

export const ACCOUNT_COLOR_OPTIONS: Array<{
  value: AccountColorKey
  label: string
}> = [
  { value: "violet", label: "Violet" },
  { value: "emerald", label: "Emerald" },
  { value: "blue", label: "Blue" },
  { value: "cyan", label: "Cyan" },
  { value: "amber", label: "Amber" },
  { value: "rose", label: "Rose" },
  { value: "slate", label: "Slate" },
]

const ACCOUNT_COLOR_THEMES: Record<AccountColorKey, AccountColorTheme> = {
  violet: {
    badgeClassName: "bg-violet-500/12 text-violet-200",
    borderClassName: "border-violet-500/30",
    dotClassName: "bg-violet-400",
    iconWrapClassName: "bg-violet-500/12 text-violet-200 ring-1 ring-violet-500/20",
    previewGlowClassName: "from-violet-500/18 via-violet-500/8 to-transparent",
  },
  emerald: {
    badgeClassName: "bg-emerald-500/12 text-emerald-200",
    borderClassName: "border-emerald-500/30",
    dotClassName: "bg-emerald-400",
    iconWrapClassName:
      "bg-emerald-500/12 text-emerald-200 ring-1 ring-emerald-500/20",
    previewGlowClassName: "from-emerald-500/18 via-emerald-500/8 to-transparent",
  },
  blue: {
    badgeClassName: "bg-blue-500/12 text-blue-200",
    borderClassName: "border-blue-500/30",
    dotClassName: "bg-blue-400",
    iconWrapClassName: "bg-blue-500/12 text-blue-200 ring-1 ring-blue-500/20",
    previewGlowClassName: "from-blue-500/18 via-blue-500/8 to-transparent",
  },
  cyan: {
    badgeClassName: "bg-cyan-500/12 text-cyan-200",
    borderClassName: "border-cyan-500/30",
    dotClassName: "bg-cyan-400",
    iconWrapClassName: "bg-cyan-500/12 text-cyan-200 ring-1 ring-cyan-500/20",
    previewGlowClassName: "from-cyan-500/18 via-cyan-500/8 to-transparent",
  },
  amber: {
    badgeClassName: "bg-amber-500/12 text-amber-200",
    borderClassName: "border-amber-500/30",
    dotClassName: "bg-amber-400",
    iconWrapClassName: "bg-amber-500/12 text-amber-200 ring-1 ring-amber-500/20",
    previewGlowClassName: "from-amber-500/18 via-amber-500/8 to-transparent",
  },
  rose: {
    badgeClassName: "bg-rose-500/12 text-rose-200",
    borderClassName: "border-rose-500/30",
    dotClassName: "bg-rose-400",
    iconWrapClassName: "bg-rose-500/12 text-rose-200 ring-1 ring-rose-500/20",
    previewGlowClassName: "from-rose-500/18 via-rose-500/8 to-transparent",
  },
  slate: {
    badgeClassName: "bg-slate-500/12 text-slate-200",
    borderClassName: "border-slate-400/30",
    dotClassName: "bg-slate-300",
    iconWrapClassName: "bg-slate-500/12 text-slate-200 ring-1 ring-slate-400/20",
    previewGlowClassName: "from-slate-400/18 via-slate-400/8 to-transparent",
  },
}

const ICONS: Record<AccountIconKey, ComponentType<{ className?: string }>> = {
  card: CreditCard,
  cash: Banknote,
  bank: Landmark,
  wallet: Wallet,
  platform: Briefcase,
  savings: PiggyBank,
  other: CircleHelp,
}

export function getAccountTypeOption(type: AccountTypeValue): AccountPresentation {
  return ACCOUNT_TYPE_OPTIONS.find((option) => option.value === type) ?? ACCOUNT_TYPE_OPTIONS[0]
}

export function getAccountTypeLabel(type: AccountTypeValue): string {
  return getAccountTypeOption(type).label
}

export function getAccountColorKey(
  type: AccountTypeValue,
  colorKey?: string | null,
): AccountColorKey {
  if (colorKey && colorKey in ACCOUNT_COLOR_THEMES) {
    return colorKey as AccountColorKey
  }

  return getAccountTypeOption(type).defaultColorKey
}

export function getAccountIconKey(
  type: AccountTypeValue,
  iconKey?: string | null,
): AccountIconKey {
  if (iconKey && iconKey in ICONS) {
    return iconKey as AccountIconKey
  }

  return getAccountTypeOption(type).defaultIconKey
}

export function getAccountColorTheme(
  type: AccountTypeValue,
  colorKey?: string | null,
): AccountColorTheme {
  return ACCOUNT_COLOR_THEMES[getAccountColorKey(type, colorKey)]
}

export function AccountIcon({
  type,
  iconKey,
  className,
}: {
  type: AccountTypeValue
  iconKey?: string | null
  className?: string
}) {
  const Icon = ICONS[getAccountIconKey(type, iconKey)]

  return <Icon className={cn("size-5", className)} />
}
