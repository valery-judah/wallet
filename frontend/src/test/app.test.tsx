import userEvent from "@testing-library/user-event"
import { screen, waitFor } from "@testing-library/react"
import {
  AccountsService,
  IncomeCategoriesService,
  SpendingCategoriesService,
  TransactionsService,
  type AccountResponse,
  type IncomeCategoryResponse,
  type SpendingCategoryResponse,
  type TransactionResponse,
} from "@/client"
import type { CategoryTreeNode } from "@/lib/categories"
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

function buildCategory(
  overrides: Partial<CategoryTreeNode> & Pick<CategoryTreeNode, "id" | "name">,
): CategoryTreeNode {
  return {
    id: overrides.id,
    name: overrides.name,
    parent_id: overrides.parent_id ?? null,
    icon: overrides.icon ?? null,
    color: overrides.color ?? null,
    sort_order: overrides.sort_order ?? 0,
    children: overrides.children ?? [],
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

function mockSharedDetailQueries({
  account = buildAccount(),
  accounts = [buildAccount()],
  spendingCategories = [
    buildCategory({
      id: "category_food",
      name: "Food",
      children: [
        buildCategory({
          id: "category_food_groceries",
          name: "Groceries",
          parent_id: "category_food",
        }),
      ],
    }),
  ],
  incomeCategories = [
    buildCategory({
      id: "income_salary",
      name: "Salary",
      children: [
        buildCategory({
          id: "income_salary_payroll",
          name: "Payroll",
          parent_id: "income_salary",
        }),
      ],
    }),
  ],
  transactions = [],
}: {
  account?: AccountResponse
  accounts?: Array<AccountResponse>
  incomeCategories?: Array<IncomeCategoryResponse>
  spendingCategories?: Array<SpendingCategoryResponse>
  transactions?: Array<TransactionResponse>
} = {}) {
  vi.spyOn(AccountsService, "accountsGetAccount").mockImplementation(async () =>
    buildSuccess(account),
  )
  vi.spyOn(AccountsService, "accountsListAccounts").mockImplementation(async () =>
    buildSuccess(accounts),
  )
  vi.spyOn(
    SpendingCategoriesService,
    "spendingCategoriesListSpendingCategories",
  ).mockImplementation(async () => buildSuccess(spendingCategories))
  vi.spyOn(
    IncomeCategoriesService,
    "incomeCategoriesListIncomeCategories",
  ).mockImplementation(async () => buildSuccess(incomeCategories))
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
        name: "Debit card",
      }),
    ).toBeInTheDocument()
    expect(screen.getByText("ARS 150.00")).toBeInTheDocument()
    expect(
      screen.getByRole("heading", {
        name: "See every account, grouped by type and balance.",
      }),
    ).toBeInTheDocument()
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

  it("opens account detail when clicking an account card", async () => {
    mockSharedDetailQueries()

    const user = userEvent.setup()
    renderApp("/accounts")

    const cardLink = await screen.findByRole("link", { name: /everyday account/i })
    await user.click(cardLink)

    expect((await screen.findAllByText("Everyday Account")).length).toBeGreaterThan(0)
    expect(screen.getByText("Current balance")).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Record transaction" })).toBeInTheDocument()
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
    expect((await screen.findAllByText("USD 150.00")).length).toBeGreaterThan(0)
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

  it("records an expense transaction and shows recent activity", async () => {
    const updatedAccount = buildAccount({
      current_balance: {
        amount_minor: 10_000,
        currency: "ARS",
      },
    })
    mockSharedDetailQueries({
      account: updatedAccount,
      accounts: [updatedAccount, buildAccount({ id: "account-456", name: "Reserve" })],
      spendingCategories: [
        buildCategory({
          id: "category_food",
          name: "Food",
          children: [
            buildCategory({
              id: "category_food_groceries",
              name: "Groceries",
              parent_id: "category_food",
            }),
            buildCategory({
              id: "category_food_restaurants",
              name: "Restaurants",
              parent_id: "category_food",
            }),
          ],
        }),
        buildCategory({
          id: "category_transport",
          name: "Transport",
          children: [
            buildCategory({
              id: "category_transport_taxi",
              name: "Taxi",
              parent_id: "category_transport",
            }),
          ],
        }),
      ],
      transactions: [buildTransaction()],
    })
    vi.spyOn(TransactionsService, "transactionsCreateTransaction").mockImplementation(async () =>
      buildSuccess(buildTransaction()),
    )

    const user = userEvent.setup()
    renderApp("/accounts/account-123")

    expect((await screen.findAllByText("ARS 100.00")).length).toBeGreaterThan(0)
    expect(screen.getByRole("heading", { name: "Recent activity" })).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Add split" }))
    await user.click(screen.getByRole("button", { name: "Add split" }))
    await user.selectOptions(
      screen.getAllByLabelText("Expense category")[0] as HTMLSelectElement,
      "category_food_groceries",
    )
    await user.selectOptions(
      screen.getAllByLabelText("Expense category")[1] as HTMLSelectElement,
      "category_food_restaurants",
    )
    await user.selectOptions(
      screen.getAllByLabelText("Expense category")[2] as HTMLSelectElement,
      "category_transport_taxi",
    )
    await user.type(screen.getAllByLabelText("Split amount")[0] as HTMLInputElement, "10")
    await user.type(screen.getAllByLabelText("Split amount")[1] as HTMLInputElement, "8")
    await user.type(screen.getAllByLabelText("Split amount")[2] as HTMLInputElement, "7")
    await user.click(screen.getByRole("button", { name: "Record transaction" }))

    await waitFor(() => {
      expect(TransactionsService.transactionsCreateTransaction).toHaveBeenCalled()
    })
    expect(TransactionsService.transactionsCreateTransaction).toHaveBeenCalledWith(
      expect.objectContaining({
        body: expect.objectContaining({
          type: "expense",
          postings: [
            { account_id: "account-123", amount_minor: -2_500, currency: "ARS" },
            {
              category_id: "category_food_groceries",
              amount_minor: 1_000,
              currency: "ARS",
            },
            {
              category_id: "category_food_restaurants",
              amount_minor: 800,
              currency: "ARS",
            },
            {
              category_id: "category_transport_taxi",
              amount_minor: 700,
              currency: "ARS",
            },
          ],
        }),
      }),
    )
    expect(await screen.findByText("Lunch")).toBeInTheDocument()
  })

  it("shows an inline error when transaction creation is rejected", async () => {
    mockSharedDetailQueries()
    vi.spyOn(TransactionsService, "transactionsCreateTransaction").mockRejectedValue(
      buildApiError(400, "expense transactions must use spending categories"),
    )

    const user = userEvent.setup()
    renderApp("/accounts/account-123")

    expect((await screen.findAllByText("Everyday Account")).length).toBeGreaterThan(0)
    await user.type(screen.getByLabelText("Split amount"), "25")
    await user.click(screen.getByRole("button", { name: "Record transaction" }))

    expect(
      await screen.findByText("expense transactions must use spending categories"),
    ).toBeInTheDocument()
  })

  it("blocks malformed decimal input before submitting the transaction", async () => {
    mockSharedDetailQueries()
    const transactionSpy = vi.spyOn(TransactionsService, "transactionsCreateTransaction")

    const user = userEvent.setup()
    renderApp("/accounts/account-123")

    expect((await screen.findAllByText("Everyday Account")).length).toBeGreaterThan(0)
    await user.type(screen.getByLabelText("Split amount"), "12.345")
    await user.click(screen.getByRole("button", { name: "Record transaction" }))

    expect(
      await screen.findByText("Split 1: Use at most 2 decimal places for ARS."),
    ).toBeInTheDocument()
    expect(transactionSpy).not.toHaveBeenCalled()
  })

  it("submits a one-posting adjustment and relies on backend balancing", async () => {
    mockSharedDetailQueries()
    vi.spyOn(TransactionsService, "transactionsCreateTransaction").mockImplementation(async () =>
      buildSuccess(
        buildTransaction({
          id: "transaction-adjustment",
          type: "adjustment",
          description: "Correction",
          postings: [
            {
              id: "posting-1",
              account_id: "account-123",
              category_id: null,
              amount_minor: 2_500,
              currency: "ARS",
              memo: null,
            },
            {
              id: "posting-2",
              account_id: "system_equity_ars",
              category_id: null,
              amount_minor: -2_500,
              currency: "ARS",
              memo: null,
            },
          ],
        }),
      ),
    )

    const user = userEvent.setup()
    renderApp("/accounts/account-123")

    expect((await screen.findAllByText("Everyday Account")).length).toBeGreaterThan(0)
    await user.click(screen.getByRole("button", { name: "Adjustment" }))
    await user.type(screen.getByLabelText("Amount"), "25")
    await user.click(screen.getByRole("button", { name: "Record transaction" }))

    await waitFor(() => {
      expect(TransactionsService.transactionsCreateTransaction).toHaveBeenCalled()
    })
    expect(TransactionsService.transactionsCreateTransaction).toHaveBeenCalledWith(
      expect.objectContaining({
        body: expect.objectContaining({
          type: "adjustment",
          postings: [{ account_id: "account-123", amount_minor: 2_500, currency: "ARS" }],
        }),
      }),
    )
  })
})
