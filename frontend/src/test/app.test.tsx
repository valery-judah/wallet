import userEvent from "@testing-library/user-event"
import { screen, waitFor } from "@testing-library/react"
import { AccountsService, type AccountResponse } from "@/client"
import { renderApp } from "@/test/render-app"

function buildAccount(overrides: Partial<AccountResponse> = {}): AccountResponse {
  return {
    id: "account-123",
    name: "Everyday Account",
    type: "card",
    currency: "ARS",
    current_balance: {
      amount_minor: 12_500,
      currency: "ARS",
    },
    status: "active",
    color_key: "violet",
    icon_key: "card",
    opened_on: "2026-06-18",
    closed_on: null,
    created_on: "2026-06-18",
    updated_on: "2026-06-18",
    ...overrides,
  }
}

function buildApiError(status: number, detail: unknown) {
  return {
    detail,
    status,
  }
}

function buildSuccess<T>(data: T) {
  return {
    data,
    request: new Request("http://localhost:8000"),
    response: new Response(),
  }
}

describe("wallet frontend routes", () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("loads and renders the accounts list", async () => {
    vi.spyOn(AccountsService, "accountsListAccounts").mockImplementation(async () =>
      buildSuccess([
        buildAccount(),
        buildAccount({
          id: "account-456",
          name: "Trips",
          type: "cash",
          current_balance: { amount_minor: 3200, currency: "USD" },
          currency: "USD",
        }),
      ]),
    )

    renderApp("/accounts")

    expect(await screen.findByText("Everyday Account")).toBeInTheDocument()
    expect(screen.getByText("Trips")).toBeInTheDocument()
    expect(screen.getByText("ARS 125.00")).toBeInTheDocument()
    expect(screen.getByText("USD 32.00")).toBeInTheDocument()
    expect(
      screen.getByRole("heading", {
        name: "See every account and its current balance.",
      }),
    ).toBeInTheDocument()
    expect(
      screen.queryByText("Template-style list, wallet-backed data."),
    ).not.toBeInTheDocument()
  })

  it("navigates to the dedicated create route from the accounts list", async () => {
    vi.spyOn(AccountsService, "accountsListAccounts").mockImplementation(async () =>
      buildSuccess([]),
    )

    const user = userEvent.setup()
    renderApp("/accounts")

    await screen.findByText("No accounts yet.")
    await user.click(screen.getByRole("link", { name: "Create an account" }))

    expect(
      await screen.findByRole("heading", {
        name: "Add a new account before money starts moving.",
      }),
    ).toBeInTheDocument()
  })

  it("creates an account from the dedicated route and lands on the detail route", async () => {
    vi.spyOn(AccountsService, "accountsCreateAccount").mockImplementation(async () =>
      buildSuccess(
        buildAccount({
          id: "account-new",
          name: "Travel Fund",
          type: "bank",
          currency: "USD",
          current_balance: { amount_minor: 15_000, currency: "USD" },
        }),
      ),
    )
    vi.spyOn(AccountsService, "accountsListAccounts").mockImplementation(async () =>
      buildSuccess([]),
    )
    vi.spyOn(AccountsService, "accountsGetAccount").mockImplementation(async () =>
      buildSuccess(
        buildAccount({
          id: "account-new",
          name: "Travel Fund",
          type: "bank",
          currency: "USD",
          current_balance: { amount_minor: 15_000, currency: "USD" },
        }),
      ),
    )

    const user = userEvent.setup()
    renderApp("/accounts/new")

    await screen.findByRole("heading", {
      name: "Add a new account before money starts moving.",
    })
    await user.type(
      screen.getByPlaceholderText("Main card, cash wallet, reserve fund"),
      "Travel Fund",
    )
    await user.selectOptions(screen.getByLabelText("Account type"), "bank")
    await user.clear(screen.getByDisplayValue("ARS"))
    await user.type(screen.getByRole("textbox", { name: /currency/i }), "USD")
    await user.clear(screen.getByRole("spinbutton", { name: /initial balance/i }))
    await user.type(
      screen.getByRole("spinbutton", { name: /initial balance/i }),
      "15000",
    )
    await user.click(screen.getByRole("button", { name: "Create account" }))

    expect((await screen.findAllByText("Travel Fund")).length).toBeGreaterThan(0)
    expect(await screen.findByText("USD 150.00")).toBeInTheDocument()
    await waitFor(() => {
      expect(AccountsService.accountsCreateAccount).toHaveBeenCalled()
    })
  })

  it("withdraws money and updates the balance", async () => {
    vi.spyOn(AccountsService, "accountsGetAccount").mockImplementation(async () =>
      buildSuccess(buildAccount()),
    )
    vi.spyOn(AccountsService, "accountsWithdrawFromAccount").mockImplementation(async () =>
      buildSuccess(
        buildAccount({
          current_balance: {
            amount_minor: 10_000,
            currency: "ARS",
          },
        }),
      ),
    )

    const user = userEvent.setup()
    renderApp("/accounts/account-123")

    expect(await screen.findByText("ARS 125.00")).toBeInTheDocument()

    await user.type(screen.getByLabelText("Amount in minor units"), "2500")
    await user.click(screen.getByRole("button", { name: "Withdraw" }))

    expect(await screen.findByText("ARS 100.00")).toBeInTheDocument()
  })

  it("shows an inline error when the withdrawal is rejected", async () => {
    vi.spyOn(AccountsService, "accountsGetAccount").mockImplementation(async () =>
      buildSuccess(buildAccount()),
    )
    vi.spyOn(AccountsService, "accountsWithdrawFromAccount").mockRejectedValue(
      buildApiError(409, "insufficient funds"),
    )

    const user = userEvent.setup()
    renderApp("/accounts/account-123")

    expect((await screen.findAllByText("Everyday Account")).length).toBeGreaterThan(0)
    await user.type(screen.getByLabelText("Amount in minor units"), "500000")
    await user.click(screen.getByRole("button", { name: "Withdraw" }))

    expect(await screen.findByText("insufficient funds")).toBeInTheDocument()
  })
})
