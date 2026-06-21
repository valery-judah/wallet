import userEvent from "@testing-library/user-event"
import { screen, waitFor } from "@testing-library/react"
import {
  IncomeCategoriesService,
  SpendingCategoriesService,
  type IncomeCategoryResponse,
  type SpendingCategoryResponse,
} from "@/client"
import type { CategoryTreeNode } from "@/lib/categories"
import { renderApp } from "@/test/render-app"

type CategoryFamily = "spending" | "income"

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

function buildDefaultTree(family: CategoryFamily): Array<CategoryTreeNode> {
  if (family === "income") {
    return [
      buildCategory({
        id: "income_salary",
        name: "Salary",
        sort_order: 10,
        children: [
          buildCategory({
            id: "income_salary_payroll",
            name: "Payroll",
            parent_id: "income_salary",
            sort_order: 10,
          }),
          buildCategory({
            id: "income_salary_bonus",
            name: "Bonus",
            parent_id: "income_salary",
            sort_order: 20,
          }),
        ],
      }),
      buildCategory({
        id: "income_investments",
        name: "Investments",
        sort_order: 20,
        children: [
          buildCategory({
            id: "income_investments_dividends",
            name: "Dividends",
            parent_id: "income_investments",
            sort_order: 10,
          }),
        ],
      }),
    ]
  }

  return [
    buildCategory({
      id: "category_food",
      name: "Food",
      sort_order: 10,
      children: [
        buildCategory({
          id: "category_food_groceries",
          name: "Groceries",
          parent_id: "category_food",
          sort_order: 10,
        }),
        buildCategory({
          id: "category_food_restaurants",
          name: "Restaurants",
          parent_id: "category_food",
          sort_order: 20,
        }),
      ],
    }),
    buildCategory({
      id: "category_housing",
      name: "Housing",
      sort_order: 20,
      children: [
        buildCategory({
          id: "category_housing_rent",
          name: "Rent",
          parent_id: "category_housing",
          sort_order: 10,
        }),
      ],
    }),
  ]
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

function cloneCategory<T extends CategoryTreeNode>(category: T): T {
  return {
    ...category,
    children: (category.children ?? []).map((child) => cloneCategory(child as T)),
  }
}

function cloneTree<T extends CategoryTreeNode>(tree: Array<T>): Array<T> {
  return tree.map((category) => cloneCategory(category))
}

function stripChildren<T extends CategoryTreeNode>(category: T): T {
  return {
    ...category,
    children: [],
  }
}

function findCategory<T extends CategoryTreeNode>(tree: Array<T>, categoryId: string): T | undefined {
  for (const category of tree) {
    if (category.id === categoryId) {
      return category
    }

    const child = (category.children ?? []).find((item) => item.id === categoryId) as T | undefined
    if (child) {
      return child
    }
  }

  return undefined
}

function sortCategories<T extends CategoryTreeNode>(categories: Array<T>): Array<T> {
  return [...categories].sort((left, right) => {
    if (left.sort_order !== right.sort_order) {
      return left.sort_order - right.sort_order
    }

    return left.name.localeCompare(right.name, undefined, { sensitivity: "base" })
  })
}

function upsertTree<T extends CategoryTreeNode>(tree: Array<T>, incoming: T): Array<T> {
  const existing = findCategory(tree, incoming.id)
  const nextCategory = {
    ...incoming,
    children: existing?.children ?? incoming.children ?? [],
  }

  const cleaned = tree
    .filter((category) => category.id !== incoming.id)
    .map((category) => ({
      ...category,
      children: (category.children ?? []).filter((child) => child.id !== incoming.id),
    }))

  if (nextCategory.parent_id === null) {
    return sortCategories(cleaned.concat(nextCategory)).map((category) => ({
      ...category,
      children: sortCategories(category.children ?? []),
    }))
  }

  return sortCategories(
    cleaned.map((category) =>
      category.id === nextCategory.parent_id
        ? {
            ...category,
            children: sortCategories([...(category.children ?? []), nextCategory]),
          }
        : category,
    ),
  ).map((category) => ({
    ...category,
    children: sortCategories(category.children ?? []),
  }))
}

function mockCategoriesApi({
  spendingTree = buildDefaultTree("spending") as Array<SpendingCategoryResponse>,
  incomeTree = buildDefaultTree("income") as Array<IncomeCategoryResponse>,
  onIncomeCreate,
  onSpendingCreate,
  onSpendingUpdate,
}: {
  incomeTree?: Array<IncomeCategoryResponse>
  onSpendingCreate?: (payload: {
    body: Record<string, unknown>
    setTree: (nextTree: Array<SpendingCategoryResponse>) => void
    tree: Array<SpendingCategoryResponse>
  }) => Promise<ReturnType<typeof buildSuccess<SpendingCategoryResponse>>>
  onSpendingUpdate?: (payload: {
    body: Record<string, unknown>
    categoryId: string
    setTree: (nextTree: Array<SpendingCategoryResponse>) => void
    tree: Array<SpendingCategoryResponse>
  }) => Promise<ReturnType<typeof buildSuccess<SpendingCategoryResponse>>>
  onIncomeCreate?: (payload: {
    body: Record<string, unknown>
    setTree: (nextTree: Array<IncomeCategoryResponse>) => void
    tree: Array<IncomeCategoryResponse>
  }) => Promise<ReturnType<typeof buildSuccess<IncomeCategoryResponse>>>
  spendingTree?: Array<SpendingCategoryResponse>
} = {}) {
  let currentSpendingTree = cloneTree(spendingTree)
  let currentIncomeTree = cloneTree(incomeTree)

  const spendingListSpy = vi
    .spyOn(SpendingCategoriesService, "spendingCategoriesListSpendingCategories")
    .mockImplementation(async () => buildSuccess(cloneTree(currentSpendingTree)))

  const spendingCreateSpy = vi
    .spyOn(SpendingCategoriesService, "spendingCategoriesCreateSpendingCategory")
    .mockImplementation(async ({ body }) => {
      if (onSpendingCreate) {
        return onSpendingCreate({
          body: body as Record<string, unknown>,
          setTree: (nextTree) => {
            currentSpendingTree = cloneTree(nextTree)
          },
          tree: cloneTree(currentSpendingTree),
        })
      }

      const created = buildCategory({
        id: `category_${String(body.name).trim().toLocaleLowerCase().replaceAll(/\s+/g, "_")}`,
        name: String(body.name),
        parent_id: (body.parent_id as string | null | undefined) ?? null,
        sort_order: Number(body.sort_order ?? 0),
      }) as SpendingCategoryResponse

      currentSpendingTree = upsertTree(currentSpendingTree, created)
      return buildSuccess(stripChildren(created))
    })

  const spendingUpdateSpy = vi
    .spyOn(SpendingCategoriesService, "spendingCategoriesUpdateSpendingCategory")
    .mockImplementation(async ({ body, path }) => {
      if (onSpendingUpdate) {
        return onSpendingUpdate({
          body: body as Record<string, unknown>,
          categoryId: path.category_id,
          setTree: (nextTree) => {
            currentSpendingTree = cloneTree(nextTree)
          },
          tree: cloneTree(currentSpendingTree),
        })
      }

      const existing = findCategory(currentSpendingTree, path.category_id)
      if (!existing) {
        throw buildApiError(404, `spending category not found: ${path.category_id}`)
      }

      const updated = buildCategory({
        ...existing,
        id: existing.id,
        name: (body.name as string | undefined) ?? existing.name,
        parent_id:
          body.parent_id === undefined
            ? existing.parent_id
            : ((body.parent_id as string | null) ?? null),
        sort_order: typeof body.sort_order === "number" ? body.sort_order : existing.sort_order,
        children: existing.children ?? [],
      }) as SpendingCategoryResponse

      currentSpendingTree = upsertTree(currentSpendingTree, updated)
      return buildSuccess(stripChildren(updated))
    })

  const incomeListSpy = vi
    .spyOn(IncomeCategoriesService, "incomeCategoriesListIncomeCategories")
    .mockImplementation(async () => buildSuccess(cloneTree(currentIncomeTree)))

  const incomeCreateSpy = vi
    .spyOn(IncomeCategoriesService, "incomeCategoriesCreateIncomeCategory")
    .mockImplementation(async ({ body }) => {
      if (onIncomeCreate) {
        return onIncomeCreate({
          body: body as Record<string, unknown>,
          setTree: (nextTree) => {
            currentIncomeTree = cloneTree(nextTree)
          },
          tree: cloneTree(currentIncomeTree),
        })
      }

      const created = buildCategory({
        id: `income_${String(body.name).trim().toLocaleLowerCase().replaceAll(/\s+/g, "_")}`,
        name: String(body.name),
        parent_id: (body.parent_id as string | null | undefined) ?? null,
        sort_order: Number(body.sort_order ?? 0),
      }) as IncomeCategoryResponse

      currentIncomeTree = upsertTree(currentIncomeTree, created)
      return buildSuccess(stripChildren(created))
    })

  const incomeUpdateSpy = vi
    .spyOn(IncomeCategoriesService, "incomeCategoriesUpdateIncomeCategory")
    .mockImplementation(async ({ body, path }) => {
      const existing = findCategory(currentIncomeTree, path.category_id)
      if (!existing) {
        throw buildApiError(404, `income category not found: ${path.category_id}`)
      }

      const updated = buildCategory({
        ...existing,
        id: existing.id,
        name: (body.name as string | undefined) ?? existing.name,
        parent_id:
          body.parent_id === undefined
            ? existing.parent_id
            : ((body.parent_id as string | null) ?? null),
        sort_order: typeof body.sort_order === "number" ? body.sort_order : existing.sort_order,
        children: existing.children ?? [],
      }) as IncomeCategoryResponse

      currentIncomeTree = upsertTree(currentIncomeTree, updated)
      return buildSuccess(stripChildren(updated))
    })

  return {
    incomeCreateSpy,
    incomeListSpy,
    incomeUpdateSpy,
    spendingCreateSpy,
    spendingListSpy,
    spendingUpdateSpy,
  }
}

describe("categories route", () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("renders the categories route and defaults to spending categories", async () => {
    mockCategoriesApi()

    renderApp("/categories")

    expect(await screen.findByRole("heading", { name: "Category trees" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Categories" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Spending" })).toHaveAttribute("aria-pressed", "true")
    expect(screen.getAllByText("Food").length).toBeGreaterThan(0)
    expect(screen.getByText("Groceries")).toBeInTheDocument()
  })

  it("shows a loading state while categories are pending", async () => {
    vi.spyOn(
      SpendingCategoriesService,
      "spendingCategoriesListSpendingCategories",
    ).mockImplementation(
      () =>
        new Promise<{
          data: Array<SpendingCategoryResponse>
          request: Request
          response: Response
        }>(() => undefined),
    )
    vi.spyOn(
      IncomeCategoriesService,
      "incomeCategoriesListIncomeCategories",
    ).mockImplementation(async () => buildSuccess([]))

    const { unmount } = renderApp("/categories")

    expect(await screen.findByText("Loading categories...")).toBeInTheDocument()
    unmount()
  })

  it("shows an API error when the active category tree fails to load", async () => {
    vi.spyOn(
      SpendingCategoriesService,
      "spendingCategoriesListSpendingCategories",
    ).mockRejectedValue(buildApiError(500, "backend unavailable"))
    vi.spyOn(
      IncomeCategoriesService,
      "incomeCategoriesListIncomeCategories",
    ).mockImplementation(async () => buildSuccess([]))

    renderApp("/categories")

    expect(await screen.findByText("Unable to load categories.")).toBeInTheDocument()
    expect(screen.getByText("backend unavailable")).toBeInTheDocument()
  })

  it("switches to income categories and renders the income tree", async () => {
    mockCategoriesApi()
    const user = userEvent.setup()

    renderApp("/categories")

    await screen.findByText("Groceries")
    await user.click(screen.getByRole("button", { name: "Income" }))

    expect(await screen.findAllByText("Salary")).not.toHaveLength(0)
    expect(screen.getByText("Payroll")).toBeInTheDocument()
    expect(screen.queryByText("Groceries")).not.toBeInTheDocument()
  })

  it("uses the fallback icon mapping for unknown categories", async () => {
    mockCategoriesApi({
      spendingTree: [
        buildCategory({
          id: "category_mystery",
          name: "Mystery",
          sort_order: 10,
          children: [],
        }) as SpendingCategoryResponse,
      ],
    })

    renderApp("/categories")

    expect(await screen.findByText("Mystery")).toBeInTheDocument()
    expect(screen.getAllByTestId("category-icon-category_mystery")[0]).toHaveAttribute(
      "data-icon-name",
      "fallback",
    )
  })

  it("creates a new spending root category from the page intro action", async () => {
    const { spendingCreateSpy } = mockCategoriesApi()
    const user = userEvent.setup()

    renderApp("/categories")

    await screen.findByText("Food")
    await user.click(screen.getByRole("button", { name: "New spending category" }))
    await user.type(screen.getByLabelText("Name"), "Hobbies")
    await user.click(screen.getByRole("button", { name: "Create spending category" }))

    expect(await screen.findAllByText("Hobbies")).not.toHaveLength(0)
    await waitFor(() => {
      expect(spendingCreateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          body: expect.objectContaining({
            name: "Hobbies",
            parent_id: null,
            sort_order: 0,
          }),
        }),
      )
    })
  })

  it("creates an income subcategory after switching tabs", async () => {
    const { incomeCreateSpy } = mockCategoriesApi()
    const user = userEvent.setup()

    renderApp("/categories")

    await screen.findByText("Food")
    await user.click(screen.getByRole("button", { name: "Income" }))
    await screen.findByText("Payroll")
    await user.click(screen.getByRole("button", { name: "Add subcategory to Salary" }))
    await user.type(screen.getByLabelText("Name"), "Freelance")
    await user.click(screen.getByRole("button", { name: "Create income category" }))

    expect(await screen.findByText("Freelance")).toBeInTheDocument()
    expect(incomeCreateSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        body: expect.objectContaining({
          name: "Freelance",
          parent_id: "income_salary",
        }),
      }),
    )
  })

  it("edits a spending child category name", async () => {
    const { spendingUpdateSpy } = mockCategoriesApi()
    const user = userEvent.setup()

    renderApp("/categories")

    await screen.findByText("Groceries")
    await user.click(screen.getByRole("button", { name: "Edit Groceries" }))
    await user.clear(screen.getByLabelText("Name"))
    await user.type(screen.getByLabelText("Name"), "Pantry")
    await user.click(screen.getByRole("button", { name: "Save spending category" }))

    expect(await screen.findByText("Pantry")).toBeInTheDocument()
    expect(spendingUpdateSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        path: { category_id: "category_food_groceries" },
      }),
    )
  })

  it("shows a duplicate-name error inline when the spending API rejects creation", async () => {
    mockCategoriesApi({
      onSpendingCreate: async () => {
        throw buildApiError(400, "category name must be unique within its sibling group")
      },
    })
    const user = userEvent.setup()

    renderApp("/categories")

    await screen.findByText("Groceries")
    await user.click(screen.getByRole("button", { name: "Add subcategory to Food" }))
    await user.type(screen.getByLabelText("Name"), "Restaurants")
    await user.click(screen.getByRole("button", { name: "Create spending category" }))

    expect(
      await screen.findByText("category name must be unique within its sibling group"),
    ).toBeInTheDocument()
  })

  it("shows an invalid-hierarchy error inline when reparenting a populated spending root", async () => {
    mockCategoriesApi({
      onSpendingUpdate: async ({ body }) => {
        if (body.parent_id) {
          throw buildApiError(400, "category with children cannot become a child category")
        }

        throw buildApiError(400, "unexpected test branch")
      },
    })
    const user = userEvent.setup()

    renderApp("/categories")

    await screen.findByText("Groceries")
    await user.click(screen.getAllByRole("button", { name: "Edit Food" })[1])
    await user.selectOptions(screen.getByLabelText("Parent category"), "category_housing")
    await user.click(screen.getByRole("button", { name: "Save spending category" }))

    expect(
      await screen.findByText("category with children cannot become a child category"),
    ).toBeInTheDocument()
  })
})
