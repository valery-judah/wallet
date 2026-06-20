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
          id: "account-789",
          name: "Reserve",
          current_balance: { amount_minor: 2_500, currency: "ARS" },
        }),
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
    expect(screen.getByText("Reserve")).toBeInTheDocument()
    expect(screen.getByText("Trips")).toBeInTheDocument()
    expect((await screen.findAllByText("ARS 125.00")).length).toBeGreaterThan(0)
    expect(screen.getAllByText("ARS 25.00").length).toBeGreaterThan(0)
    expect(screen.getAllByText("USD 32.00").length).toBeGreaterThan(0)
    expect(
      screen.getByRole("heading", {
        name: "Card",
      }),
    ).toBeInTheDocument()
    expect(screen.getByText("ARS 150.00")).toBeInTheDocument()
    expect(
      screen.getByRole("heading", {
        name: "See every account, grouped by type and balance.",
      }),
    ).toBeInTheDocument()
    expect(screen.getByText("Tracked balance")).toBeInTheDocument()
    expect(screen.getByText("Lifecycle")).toBeInTheDocument()
    expect(screen.getAllByText("Open account").length).toBeGreaterThan(0)
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
        name: "Set up a new account.",
      }),
    ).toBeInTheDocument()
    expect(screen.getByText("Tips")).toBeInTheDocument()
    expect(screen.getByText("Each account uses one currency.")).toBeInTheDocument()
    expect(screen.getByText("Track your accounts in one place.")).toBeInTheDocument()
  })

  it("opens account detail when clicking an account card", async () => {
    vi.spyOn(AccountsService, "accountsListAccounts").mockImplementation(async () =>
      buildSuccess([buildAccount()]),
    )
    vi.spyOn(AccountsService, "accountsGetAccount").mockImplementation(async () =>
      buildSuccess(buildAccount()),
    )

    const user = userEvent.setup()
    renderApp("/accounts")

    const cardLink = await screen.findByRole("link", { name: /everyday account/i })
    await user.click(cardLink)

    expect((await screen.findAllByText("Everyday Account")).length).toBeGreaterThan(0)
    expect(screen.getByText("Current balance")).toBeInTheDocument()
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
      name: "Set up a new account.",
    })
    expect(
      screen.getByText(
        "Choose the account type, currency, and starting balance for this account.",
      ),
    ).toBeInTheDocument()
    expect(screen.getByText("Account setup")).toBeInTheDocument()
    await user.type(
      screen.getByPlaceholderText("Main card, cash wallet, reserve fund"),
      "Travel Fund",
    )
    await user.click(screen.getByRole("radio", { name: /bank account/i }))
    await user.clear(screen.getByDisplayValue("ARS"))
    await user.type(screen.getByRole("textbox", { name: /currency/i }), "USD")
    await user.clear(screen.getByRole("textbox", { name: /starting balance/i }))
    await user.type(
      screen.getByRole("textbox", { name: /starting balance/i }),
      "150",
    )
    expect(screen.getAllByText("USD 150.00").length).toBeGreaterThan(0)
    await user.click(screen.getByRole("button", { name: "Create account" }))

    expect((await screen.findAllByText("Travel Fund")).length).toBeGreaterThan(0)
    expect((await screen.findAllByText("USD 150.00")).length).toBeGreaterThan(0)
    await waitFor(() => {
      expect(AccountsService.accountsCreateAccount).toHaveBeenCalled()
    })
    expect(AccountsService.accountsCreateAccount).toHaveBeenCalledWith(
      expect.objectContaining({
        body: expect.objectContaining({
          current_balance_minor: 15_000,
          currency: "USD",
          name: "Travel Fund",
          type: "bank",
        }),
      }),
    )
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

    expect((await screen.findAllByText("ARS 125.00")).length).toBeGreaterThan(0)
    expect(screen.getByText("Opened on")).toBeInTheDocument()
    expect(screen.getByText("Closed on")).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Close account" })).toBeInTheDocument()
    expect(screen.getAllByRole("heading", { name: "Withdraw money" })).toHaveLength(1)

    await user.type(screen.getByLabelText("Amount"), "25")
    await user.click(screen.getByRole("button", { name: "Withdraw" }))

    expect((await screen.findAllByText("ARS 100.00")).length).toBeGreaterThan(0)
    expect(AccountsService.accountsWithdrawFromAccount).toHaveBeenCalledWith(
      expect.objectContaining({
        body: { amount_minor: 2_500, currency: "ARS" },
        path: { account_id: "account-123" },
      }),
    )
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
    await user.type(screen.getByLabelText("Amount"), "5000")
    await user.click(screen.getByRole("button", { name: "Withdraw" }))

    expect(await screen.findByText("insufficient funds")).toBeInTheDocument()
  })

  it("blocks malformed decimal input before submitting the withdrawal", async () => {
    vi.spyOn(AccountsService, "accountsGetAccount").mockImplementation(async () =>
      buildSuccess(buildAccount()),
    )
    const withdrawSpy = vi.spyOn(AccountsService, "accountsWithdrawFromAccount")

    const user = userEvent.setup()
    renderApp("/accounts/account-123")

    expect((await screen.findAllByText("Everyday Account")).length).toBeGreaterThan(0)
    await user.type(screen.getByLabelText("Amount"), "12.345")
    await user.click(screen.getByRole("button", { name: "Withdraw" }))

    expect(await screen.findByText("Use at most 2 decimal places for ARS.")).toBeInTheDocument()
    expect(withdrawSpy).not.toHaveBeenCalled()
  })
})
