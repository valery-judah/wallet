import userEvent from "@testing-library/user-event"
import { screen, waitFor } from "@testing-library/react"
import { CardsService, type CardResponse } from "@/client"
import { renderApp } from "@/test/render-app"

function buildCard(overrides: Partial<CardResponse> = {}): CardResponse {
  return {
    id: "card-123",
    name: "Everyday Card",
    currency: "ARS",
    balance: {
      amount_minor: 12_500,
      currency: "ARS",
    },
    created_on: "2026-06-18",
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

  it("loads and renders the cards list", async () => {
    vi.spyOn(CardsService, "cardsListCards").mockImplementation(async () =>
      buildSuccess([
        buildCard(),
        buildCard({ id: "card-456", name: "Trips", balance: { amount_minor: 3200, currency: "USD" }, currency: "USD" }),
      ]),
    )

    renderApp("/cards")

    expect(await screen.findByText("Everyday Card")).toBeInTheDocument()
    expect(screen.getByText("Trips")).toBeInTheDocument()
    expect(screen.getByText("ARS 125.00")).toBeInTheDocument()
    expect(screen.getByText("USD 32.00")).toBeInTheDocument()
    expect(
      screen.getByRole("heading", {
        name: "See every card and its current balance.",
      }),
    ).toBeInTheDocument()
    expect(
      screen.queryByText("Template-style list, wallet-backed data."),
    ).not.toBeInTheDocument()
  })

  it("navigates to the dedicated create route from the cards list", async () => {
    vi.spyOn(CardsService, "cardsListCards").mockImplementation(async () =>
      buildSuccess([]),
    )

    const user = userEvent.setup()
    renderApp("/cards")

    await screen.findByText("No cards yet.")
    await user.click(screen.getByRole("link", { name: "Create a card" }))

    expect(
      await screen.findByRole("heading", {
        name: "Add a fresh card before money starts moving.",
      }),
    ).toBeInTheDocument()
  })

  it("creates a card from the dedicated route and lands on the detail route", async () => {
    vi.spyOn(CardsService, "cardsCreateCard").mockImplementation(async () =>
      buildSuccess(
        buildCard({ id: "card-new", name: "Travel Fund", currency: "USD", balance: { amount_minor: 0, currency: "USD" } }),
      ),
    )
    vi.spyOn(CardsService, "cardsListCards").mockImplementation(async () =>
      buildSuccess([]),
    )
    vi.spyOn(CardsService, "cardsGetCard").mockImplementation(async () =>
      buildSuccess(
        buildCard({ id: "card-new", name: "Travel Fund", currency: "USD", balance: { amount_minor: 0, currency: "USD" } }),
      ),
    )

    const user = userEvent.setup()
    renderApp("/cards/new")

    await screen.findByRole("heading", {
      name: "Add a fresh card before money starts moving.",
    })
    expect(
      screen.queryByText(
        "This keeps the template naming, but creates a wallet card in the backend.",
      ),
    ).not.toBeInTheDocument()
    await user.type(
      screen.getByPlaceholderText("Groceries, travel, emergency cash"),
      "Travel Fund",
    )
    await user.clear(screen.getByDisplayValue("ARS"))
    await user.type(screen.getByRole("textbox", { name: /currency/i }), "USD")
    await user.click(screen.getByRole("button", { name: "Create card" }))

    expect(await screen.findByText("Travel Fund")).toBeInTheDocument()
    await waitFor(() => {
      expect(CardsService.cardsCreateCard).toHaveBeenCalled()
    })
  })

  it("withdraws money and updates the balance", async () => {
    vi.spyOn(CardsService, "cardsGetCard").mockImplementation(async () =>
      buildSuccess(buildCard()),
    )
    vi.spyOn(CardsService, "cardsWithdrawFromCard").mockImplementation(async () =>
      buildSuccess(
        buildCard({
          balance: {
            amount_minor: 10_000,
            currency: "ARS",
          },
        }),
      ),
    )

    const user = userEvent.setup()
    renderApp("/cards/card-123")

    expect(await screen.findByText("ARS 125.00")).toBeInTheDocument()

    await user.type(screen.getByLabelText("Amount in minor units"), "2500")
    await user.click(screen.getByRole("button", { name: "Withdraw" }))

    expect(await screen.findByText("ARS 100.00")).toBeInTheDocument()
  })

  it("shows an inline error when the withdrawal is rejected", async () => {
    vi.spyOn(CardsService, "cardsGetCard").mockImplementation(async () =>
      buildSuccess(buildCard()),
    )
    vi.spyOn(CardsService, "cardsWithdrawFromCard").mockRejectedValue(
      buildApiError(409, "insufficient funds"),
    )

    const user = userEvent.setup()
    renderApp("/cards/card-123")

    await screen.findByText("Everyday Card")
    await user.type(screen.getByLabelText("Amount in minor units"), "500000")
    await user.click(screen.getByRole("button", { name: "Withdraw" }))

    expect(await screen.findByText("insufficient funds")).toBeInTheDocument()
  })
})
