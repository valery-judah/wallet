import userEvent from "@testing-library/user-event"
import { screen, waitFor } from "@testing-library/react"
import {
  AccountsService,
  SpendingCategoriesService,
  TransactionsService,
  type AccountResponse,
  type SpendingCategoryResponse,
  type TransactionResponse,
} from "@/client"
import { renderApp } from "@/test/render-app"

function buildAccount(overrides: Partial<AccountResponse> = {}): AccountResponse {
  return {
    id: "account-123",
    name: "Everyday Account",
    type: "debit_card",
    currency: "ARS",
    current_balance: {
      amount_minor: 12_500,
      currency: "ARS",
    },
    color_key: "violet",
    opened_on: "2026-06-18",
    archived_at: null,
    created_on: "2026-06-18",
    updated_on: "2026-06-18",
    ...overrides,
  }
}

function buildTransaction(
  overrides: Partial<TransactionResponse> = {},
): TransactionResponse {
  return {
    id: "transaction-123",
    occurred_on: "2026-06-20",
    posted_on: "2026-06-20",
    description: "Lunch",
    merchant_name: null,
    notes: null,
    status: "posted",
    type: "expense",
    postings: [
      {
        id: "posting-1",
        account_id: "account-123",
        category_id: null,
        amount_minor: -2_500,
        currency: "ARS",
        memo: null,
      },
      {
        id: "posting-2",
        account_id: null,
        category_id: "category_food_groceries",
        amount_minor: 2_500,
        currency: "ARS",
        memo: null,
      },
    ],
    created_on: "2026-06-20",
    updated_on: "2026-06-20",
    ...overrides,
  }
}

function buildSpendingCategoryTree(): Array<SpendingCategoryResponse> {
  return [
    {
      id: "category_food",
      name: "Food",
      parent_id: null,
      icon: null,
      color: null,
      sort_order: 10,
      children: [
        {
          id: "category_food_groceries",
          name: "Groceries",
          parent_id: "category_food",
          icon: null,
          color: null,
          sort_order: 20,
          children: [],
        },
      ],
    },
  ]
}

function buildSuccess<T>(data: T) {
  return {
    data,
    request: new Request("http://localhost:8000"),
    response: new Response(),
  }
}

function mockSharedDetailQueries({
  account = buildAccount(),
  accounts = [buildAccount()],
  transactions = [],
}: {
  account?: AccountResponse
  accounts?: Array<AccountResponse>
  transactions?: Array<TransactionResponse>
} = {}) {
  vi.spyOn(AccountsService, "accountsGetAccount").mockImplementation(async () =>
    buildSuccess(account),
  )
  vi.spyOn(AccountsService, "accountsListAccounts").mockImplementation(async () =>
    buildSuccess(accounts),
  )
  vi.spyOn(TransactionsService, "transactionsListTransactions").mockImplementation(async () =>
    buildSuccess(transactions),
  )
}

function mockTransactionRouteQueries({
  accounts = [buildAccount()],
  spendingCategories = buildSpendingCategoryTree(),
  transactions = [buildTransaction()],
}: {
  accounts?: Array<AccountResponse>
  spendingCategories?: Array<SpendingCategoryResponse>
  transactions?: Array<TransactionResponse>
} = {}) {
  vi.spyOn(AccountsService, "accountsListAccounts").mockImplementation(async () =>
    buildSuccess(accounts),
  )
  vi.spyOn(SpendingCategoriesService, "spendingCategoriesListSpendingCategories").mockImplementation(
    async () => buildSuccess(spendingCategories),
  )
  vi.spyOn(TransactionsService, "transactionsListTransactions").mockImplementation(async () =>
    buildSuccess(transactions),
  )
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
        name: "Accounts",
      }),
    ).toBeInTheDocument()
    expect(screen.getByText(/Total balance:/)).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /add account/i })).toBeInTheDocument()
    expect(screen.getAllByText("Healthy Status").length).toBeGreaterThan(0)
  })

  it("shows a visual edit affordance only for active account cards", async () => {
    mockSharedDetailQueries({
      accounts: [
        buildAccount(),
        buildAccount({
          id: "account-archived",
          name: "Archived Reserve",
          archived_at: "2026-06-19",
        }),
      ],
    })

    const user = userEvent.setup()
    renderApp("/accounts")

    expect(
      await screen.findByTestId("account-edit-affordance-account-123"),
    ).toBeInTheDocument()
    expect(
      screen.queryByTestId("account-edit-affordance-account-archived"),
    ).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /edit/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: /edit/i })).not.toBeInTheDocument()

    await user.click(
      screen.getByRole("link", {
        name: /everyday account/i,
      }),
    )

    expect((await screen.findAllByText("Everyday Account")).length).toBeGreaterThan(0)
    expect(screen.getByText("Current balance")).toBeInTheDocument()
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
    expect(
      screen.getByText("Choose the account type, currency, and opening balance for this account."),
    ).toBeInTheDocument()
    expect(screen.getByText("Each account uses one currency.")).toBeInTheDocument()
  })

  it("opens account detail as a read-only info page", async () => {
    mockSharedDetailQueries()

    const user = userEvent.setup()
    renderApp("/accounts")

    const cardLink = await screen.findByRole("link", { name: /everyday account/i })
    await user.click(cardLink)

    expect((await screen.findAllByText("Everyday Account")).length).toBeGreaterThan(0)
    expect(screen.getByText("Current balance")).toBeInTheDocument()
    expect(screen.getByText("Transaction count")).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Recent activity" })).toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: "Record transaction" })).not.toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: "Account profile" })).not.toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: "Archive account" })).not.toBeInTheDocument()
  })

  it("creates an account from the dedicated route and lands on the detail route", async () => {
    vi.spyOn(AccountsService, "accountsCreateAccount").mockImplementation(async () =>
      buildSuccess(
        buildAccount({
          id: "account-new",
          name: "Travel Fund",
          type: "bank_account",
          currency: "USD",
          current_balance: { amount_minor: 15_000, currency: "USD" },
        }),
      ),
    )
    mockSharedDetailQueries({
      account: buildAccount({
        id: "account-new",
        name: "Travel Fund",
        type: "bank_account",
        currency: "USD",
        current_balance: { amount_minor: 15_000, currency: "USD" },
      }),
      accounts: [],
    })

    const user = userEvent.setup()
    renderApp("/accounts/new")

    await screen.findByRole("heading", {
      name: "Set up a new account.",
    })
    await user.type(
      screen.getByPlaceholderText("Main card, cash wallet, reserve fund"),
      "Travel Fund",
    )
    await user.click(screen.getByRole("radio", { name: /bank account/i }))
    await user.clear(screen.getByDisplayValue("ARS"))
    await user.type(screen.getByRole("textbox", { name: /currency/i }), "USD")
    await user.clear(screen.getByRole("textbox", { name: /opening balance/i }))
    await user.type(
      screen.getByRole("textbox", { name: /opening balance/i }),
      "150",
    )
    expect(screen.getAllByText("USD 150.00").length).toBeGreaterThan(0)
    await user.click(screen.getByRole("button", { name: "Create account" }))

    expect((await screen.findAllByText("Travel Fund")).length).toBeGreaterThan(0)
    expect(screen.getByRole("heading", { name: "Recent activity" })).toBeInTheDocument()
    await waitFor(() => {
      expect(AccountsService.accountsCreateAccount).toHaveBeenCalled()
    })
    expect(AccountsService.accountsCreateAccount).toHaveBeenCalledWith(
      expect.objectContaining({
        body: expect.objectContaining({
          opening_balance_minor: 15_000,
          currency: "USD",
          name: "Travel Fund",
          type: "bank_account",
        }),
      }),
    )
  })

  it("shows derived metrics and only the latest five account transactions", async () => {
    mockSharedDetailQueries({
      account: buildAccount({
        current_balance: {
          amount_minor: 8_300,
          currency: "ARS",
        },
      }),
      transactions: [
        buildTransaction({
          id: "transaction-1",
          occurred_on: "2026-06-22",
          created_on: "2026-06-23",
          description: "Salary payout",
          type: "income",
          postings: [
            {
              id: "posting-1",
              account_id: "account-123",
              category_id: null,
              amount_minor: 9_000,
              currency: "ARS",
              memo: null,
            },
            {
              id: "posting-2",
              account_id: null,
              category_id: "income_salary",
              amount_minor: -9_000,
              currency: "ARS",
              memo: null,
            },
          ],
        }),
        buildTransaction({
          id: "transaction-2",
          occurred_on: "2026-06-22",
          created_on: "2026-06-22",
          description: "Freelance client",
          type: "income",
          postings: [
            {
              id: "posting-1",
              account_id: "account-123",
              category_id: null,
              amount_minor: 2_000,
              currency: "ARS",
              memo: null,
            },
            {
              id: "posting-2",
              account_id: null,
              category_id: "income_business",
              amount_minor: -2_000,
              currency: "ARS",
              memo: null,
            },
          ],
        }),
        buildTransaction({
          id: "transaction-3",
          occurred_on: "2026-06-20",
          created_on: "2026-06-20",
          description: "Groceries",
          postings: [
            {
              id: "posting-1",
              account_id: "account-123",
              category_id: null,
              amount_minor: -1_500,
              currency: "ARS",
              memo: null,
            },
            {
              id: "posting-2",
              account_id: null,
              category_id: "category_food_groceries",
              amount_minor: 1_500,
              currency: "ARS",
              memo: null,
            },
          ],
        }),
        buildTransaction({
          id: "transaction-4",
          occurred_on: "2026-06-19",
          created_on: "2026-06-19",
          description: "Subway",
          postings: [
            {
              id: "posting-1",
              account_id: "account-123",
              category_id: null,
              amount_minor: -700,
              currency: "ARS",
              memo: null,
            },
            {
              id: "posting-2",
              account_id: null,
              category_id: "category_transport",
              amount_minor: 700,
              currency: "ARS",
              memo: null,
            },
          ],
        }),
        buildTransaction({
          id: "transaction-5",
          occurred_on: "2026-06-18",
          created_on: "2026-06-18",
          description: "Rent",
          postings: [
            {
              id: "posting-1",
              account_id: "account-123",
              category_id: null,
              amount_minor: -1_500,
              currency: "ARS",
              memo: null,
            },
            {
              id: "posting-2",
              account_id: null,
              category_id: "category_home",
              amount_minor: 1_500,
              currency: "ARS",
              memo: null,
            },
          ],
        }),
        buildTransaction({
          id: "transaction-6",
          occurred_on: "2026-06-17",
          created_on: "2026-06-17",
          description: "Seed adjustment",
          type: "adjustment",
          postings: [
            {
              id: "posting-1",
              account_id: "account-123",
              category_id: null,
              amount_minor: 1_000,
              currency: "ARS",
              memo: null,
            },
            {
              id: "posting-2",
              account_id: "system_equity_ars",
              category_id: null,
              amount_minor: -1_000,
              currency: "ARS",
              memo: null,
            },
          ],
        }),
      ],
    })

    renderApp("/accounts/account-123")

    expect(await screen.findByText("ARS 83.00")).toBeInTheDocument()
    expect(screen.getByText("+ARS 120.00")).toBeInTheDocument()
    expect(screen.getByText("-ARS 37.00")).toBeInTheDocument()
    expect(screen.getByText("6")).toBeInTheDocument()
    expect(screen.getAllByText("Salary payout").length).toBeGreaterThan(0)
    expect(screen.getByText("2026-06-22")).toBeInTheDocument()
    expect(screen.getByText("Freelance client")).toBeInTheDocument()
    expect(screen.getByText("Groceries")).toBeInTheDocument()
    expect(screen.getByText("Subway")).toBeInTheDocument()
    expect(screen.getByText("Rent")).toBeInTheDocument()
    expect(screen.queryByText("Seed adjustment")).not.toBeInTheDocument()
  })

  it("shows an empty read-only activity state for accounts with no transactions", async () => {
    mockSharedDetailQueries()

    renderApp("/accounts/account-123")

    expect((await screen.findAllByText("Everyday Account")).length).toBeGreaterThan(0)
    expect(screen.getByText("+ARS 0.00")).toBeInTheDocument()
    expect(screen.getByText("-ARS 0.00")).toBeInTheDocument()
    expect(screen.getByText("No activity yet")).toBeInTheDocument()
    expect(screen.getByText("No transactions found for this account.")).toBeInTheDocument()
    expect(screen.queryByText("View Full History")).not.toBeInTheDocument()
  })

  it("adds transactions to the sidebar and posts a withdraw-style expense transaction", async () => {
    vi.spyOn(TransactionsService, "transactionsCreateTransaction").mockImplementation(async () =>
      buildSuccess(
        buildTransaction({
          id: "transaction-new",
          description: "Corner cafe",
          merchant_name: "Corner cafe",
          postings: [
            {
              id: "posting-account",
              account_id: "account-123",
              category_id: null,
              amount_minor: -1_250,
              currency: "ARS",
              memo: null,
            },
            {
              id: "posting-category",
              account_id: null,
              category_id: "category_food_groceries",
              amount_minor: 1_250,
              currency: "ARS",
              memo: null,
            },
          ],
        }),
      ),
    )
    mockTransactionRouteQueries()

    const user = userEvent.setup()
    renderApp("/transactions")

    expect(
      await screen.findByRole("heading", {
        name: "Withdraw from an account.",
      }),
    ).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Transactions" })).toBeInTheDocument()
    expect(screen.getByText("Recent withdrawals")).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText("Spending category"), "category_food_groceries")
    await user.type(screen.getByLabelText("Amount"), "12.50")
    await user.type(screen.getByLabelText("Merchant"), "Corner cafe")
    await user.click(screen.getByRole("button", { name: "Withdraw" }))

    await waitFor(() => {
      expect(TransactionsService.transactionsCreateTransaction).toHaveBeenCalled()
    })
    expect(TransactionsService.transactionsCreateTransaction).toHaveBeenCalledWith(
      expect.objectContaining({
        body: expect.objectContaining({
          type: "expense",
          merchant_name: "Corner cafe",
          description: "Corner cafe",
          postings: [
            expect.objectContaining({
              account_id: "account-123",
              amount_minor: -1_250,
              currency: "ARS",
            }),
            expect.objectContaining({
              category_id: "category_food_groceries",
              amount_minor: 1_250,
              currency: "ARS",
            }),
          ],
        }),
      }),
    )
    expect(
      await screen.findByText("Recorded ARS 12.50 from Everyday Account."),
    ).toBeInTheDocument()
  })
})
