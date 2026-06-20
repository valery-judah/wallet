import {
  formatMajorAmountInput,
  formatMoney,
  getCurrencyMinorUnit,
  parseMajorAmount,
} from "@/lib/money"

describe("money helpers", () => {
  it("parses major amounts into minor units for two-decimal currencies", () => {
    expect(parseMajorAmount("300", "ARS", { allowZero: true })).toEqual({
      amountMinor: 30_000,
    })
    expect(parseMajorAmount("300.50", "ARS", { allowZero: true })).toEqual({
      amountMinor: 30_050,
    })
  })

  it("accepts zero for account opening but rejects it for withdrawals", () => {
    expect(parseMajorAmount("0", "ARS", { allowZero: true })).toEqual({
      amountMinor: 0,
    })
    expect(parseMajorAmount("0", "ARS")).toEqual({
      error: "Enter an amount greater than 0.",
    })
  })

  it("rejects too many decimals for the currency", () => {
    expect(parseMajorAmount("12.345", "ARS", { allowZero: true })).toEqual({
      error: "Use at most 2 decimal places for ARS.",
    })
  })

  it("uses ISO minor units for zero-decimal currencies", () => {
    expect(getCurrencyMinorUnit("JPY")).toBe(0)
    expect(parseMajorAmount("300", "JPY")).toEqual({
      amountMinor: 300,
    })
    expect(parseMajorAmount("300.5", "JPY")).toEqual({
      error: "JPY does not use decimal places.",
    })
    expect(formatMoney(300, "JPY")).toBe("JPY 300")
    expect(formatMajorAmountInput(300, "JPY")).toBe("300")
  })

  it("falls back to two decimals for unknown currencies", () => {
    expect(getCurrencyMinorUnit("ZZZ")).toBe(2)
    expect(parseMajorAmount("12.34", "ZZZ")).toEqual({
      amountMinor: 1_234,
    })
    expect(formatMoney(1_234, "ZZZ")).toBe("ZZZ 12.34")
    expect(formatMajorAmountInput(1_234, "ZZZ")).toBe("12.34")
  })
})
