import { CURRENCY_MINOR_UNIT_BY_CODE } from "@/lib/generated-currency-meta"

const DEFAULT_MINOR_UNIT = 2
const MAJOR_AMOUNT_PATTERN = /^\d+(?:\.(\d*))?$/

type ParseMajorAmountOptions = {
  allowZero?: boolean
}

type ParseMajorAmountResult =
  | {
      amountMinor: number
      error?: undefined
    }
  | {
      amountMinor?: undefined
      error: string
    }

export function getCurrencyMinorUnit(currency: string): number {
  return CURRENCY_MINOR_UNIT_BY_CODE[normalizeCurrencyCode(currency)] ?? DEFAULT_MINOR_UNIT
}

export function parseMajorAmount(
  input: string,
  currency: string,
  options: ParseMajorAmountOptions = {},
): ParseMajorAmountResult {
  const trimmed = input.trim()
  const normalizedCurrency = normalizeCurrencyCode(currency)
  const minorUnit = getCurrencyMinorUnit(normalizedCurrency)

  if (trimmed.length === 0) {
    return { error: "Enter an amount." }
  }

  const match = MAJOR_AMOUNT_PATTERN.exec(trimmed)

  if (!match) {
    return { error: "Use digits with an optional decimal point." }
  }

  const fractionDigits = match[1] ?? ""

  if (fractionDigits.length > minorUnit) {
    return minorUnit === 0
      ? { error: `${normalizedCurrency} does not use decimal places.` }
      : { error: `Use at most ${minorUnit} decimal places for ${normalizedCurrency}.` }
  }

  const wholePart = trimmed.split(".", 1)[0] ?? "0"
  const divisor = 10 ** minorUnit
  const fractionPart =
    minorUnit === 0 ? 0 : Number.parseInt(fractionDigits.padEnd(minorUnit, "0") || "0", 10)
  const amountMinor = Number.parseInt(wholePart, 10) * divisor + fractionPart

  if (!Number.isSafeInteger(amountMinor)) {
    return { error: "Amount is too large." }
  }

  if (!options.allowZero && amountMinor <= 0) {
    return { error: "Enter an amount greater than 0." }
  }

  return { amountMinor }
}

export function formatMajorAmountInput(amountMinor: number, currency: string): string {
  const minorUnit = getCurrencyMinorUnit(currency)
  const sign = amountMinor < 0 ? "-" : ""
  const absoluteAmountMinor = Math.abs(amountMinor)

  if (minorUnit === 0) {
    return `${sign}${absoluteAmountMinor}`
  }

  const divisor = 10 ** minorUnit
  const wholePart = Math.floor(absoluteAmountMinor / divisor)
  const fractionText = `${absoluteAmountMinor % divisor}`.padStart(minorUnit, "0")
  const trimmedFractionText = fractionText.replace(/0+$/, "")

  if (trimmedFractionText.length === 0) {
    return `${sign}${wholePart}`
  }

  return `${sign}${wholePart}.${trimmedFractionText}`
}

export function formatMoney(amountMinor: number, currency: string): string {
  const normalizedCurrency = normalizeCurrencyCode(currency)
  const minorUnit = getCurrencyMinorUnit(normalizedCurrency)
  const amount = amountMinor / 10 ** minorUnit
  const formattedAmount = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: minorUnit,
    maximumFractionDigits: minorUnit,
  }).format(amount)

  return `${normalizedCurrency} ${formattedAmount}`
}

function normalizeCurrencyCode(currency: string): string {
  return currency.trim().toUpperCase()
}
