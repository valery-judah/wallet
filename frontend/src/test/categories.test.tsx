import userEvent from "@testing-library/user-event"
import { screen, waitFor } from "@testing-library/react"
import {
  SpendingCategoriesService,
  type SpendingCategoryResponse,
} from "@/client"
import { renderApp } from "@/test/render-app"

function buildCategory(
  overrides: Partial<SpendingCategoryResponse> & Pick<SpendingCategoryResponse, "id" | "name">,
): SpendingCategoryResponse {
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

function buildDefaultTree(): Array<SpendingCategoryResponse> {
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

function cloneCategory(category: SpendingCategoryResponse): SpendingCategoryResponse {
  return {
    ...category,
    children: (category.children ?? []).map(cloneCategory),
  }
}

function cloneTree(tree: Array<SpendingCategoryResponse>): Array<SpendingCategoryResponse> {
  return tree.map(cloneCategory)
}

function stripChildren(category: SpendingCategoryResponse): SpendingCategoryResponse {
  return {
    ...category,
    children: [],
  }
}

function findCategory(
  tree: Array<SpendingCategoryResponse>,
  categoryId: string,
): SpendingCategoryResponse | undefined {
  for (const category of tree) {
    if (category.id === categoryId) {
      return category
    }

    const child = (category.children ?? []).find((item) => item.id === categoryId)
    if (child) {
      return child
    }
  }

  return undefined
}

function sortCategories(
  categories: Array<SpendingCategoryResponse>,
): Array<SpendingCategoryResponse> {
  return [...categories].sort((left, right) => {
    if (left.sort_order !== right.sort_order) {
      return left.sort_order - right.sort_order
    }

    return left.name.localeCompare(right.name, undefined, { sensitivity: "base" })
  })
}

function upsertTree(
  tree: Array<SpendingCategoryResponse>,
  incoming: SpendingCategoryResponse,
): Array<SpendingCategoryResponse> {
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
  initialTree = buildDefaultTree(),
  onCreate,
  onUpdate,
}: {
  initialTree?: Array<SpendingCategoryResponse>
  onCreate?: (payload: {
    body: Record<string, unknown>
    setTree: (nextTree: Array<SpendingCategoryResponse>) => void
    tree: Array<SpendingCategoryResponse>
  }) => Promise<ReturnType<typeof buildSuccess<SpendingCategoryResponse>>>
  onUpdate?: (payload: {
    body: Record<string, unknown>
    categoryId: string
    setTree: (nextTree: Array<SpendingCategoryResponse>) => void
    tree: Array<SpendingCategoryResponse>
  }) => Promise<ReturnType<typeof buildSuccess<SpendingCategoryResponse>>>
} = {}) {
  let currentTree = cloneTree(initialTree)

  const listSpy = vi
    .spyOn(SpendingCategoriesService, "spendingCategoriesListSpendingCategories")
    .mockImplementation(async () => buildSuccess(cloneTree(currentTree)))

  const createSpy = vi
    .spyOn(SpendingCategoriesService, "spendingCategoriesCreateSpendingCategory")
    .mockImplementation(async ({ body }) => {
      if (onCreate) {
        return onCreate({
          body: body as Record<string, unknown>,
          setTree: (nextTree) => {
            currentTree = cloneTree(nextTree)
          },
          tree: cloneTree(currentTree),
        })
      }

      const created = buildCategory({
        id: `category_${String(body.name).trim().toLocaleLowerCase().replaceAll(/\s+/g, "_")}`,
        name: String(body.name),
        parent_id: (body.parent_id as string | null | undefined) ?? null,
        sort_order: Number(body.sort_order ?? 0),
      })

      currentTree = upsertTree(currentTree, created)
      return buildSuccess(stripChildren(created))
    })

  const updateSpy = vi
    .spyOn(SpendingCategoriesService, "spendingCategoriesUpdateSpendingCategory")
    .mockImplementation(async ({ body, path }) => {
      if (onUpdate) {
        return onUpdate({
          body: body as Record<string, unknown>,
          categoryId: path.category_id,
          setTree: (nextTree) => {
            currentTree = cloneTree(nextTree)
          },
          tree: cloneTree(currentTree),
        })
      }

      const existing = findCategory(currentTree, path.category_id)

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
        sort_order:
          typeof body.sort_order === "number" ? body.sort_order : existing.sort_order,
        children: existing.children ?? [],
      })

      currentTree = upsertTree(currentTree, updated)
      return buildSuccess(stripChildren(updated))
    })

  return { createSpy, listSpy, updateSpy }
}

describe("spending categories route", () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("renders the categories route, sidebar entry, and default selected root", async () => {
    mockCategoriesApi()

    renderApp("/categories")

    expect(
      await screen.findByRole("heading", { name: "Spending categories" }),
    ).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Categories" })).toBeInTheDocument()
    expect(screen.getAllByText("Food").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Housing").length).toBeGreaterThan(0)
    expect(screen.getByText("Groceries")).toBeInTheDocument()
    expect(screen.getByText("Restaurants")).toBeInTheDocument()
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

    const { unmount } = renderApp("/categories")

    expect(await screen.findByText("Loading categories...")).toBeInTheDocument()
    unmount()
  })

  it("shows an API error when categories fail to load", async () => {
    vi.spyOn(
      SpendingCategoriesService,
      "spendingCategoriesListSpendingCategories",
    ).mockRejectedValue(buildApiError(500, "backend unavailable"))

    renderApp("/categories")

    expect(await screen.findByText("Unable to load categories.")).toBeInTheDocument()
    expect(screen.getByText("backend unavailable")).toBeInTheDocument()
  })

  it("switches the selected root category and renders its children", async () => {
    mockCategoriesApi()
    const user = userEvent.setup()

    renderApp("/categories")

    expect(await screen.findByText("Groceries")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Housing 1 subcategory" }))

    expect(await screen.findByText("Rent")).toBeInTheDocument()
    expect(screen.queryByText("Groceries")).not.toBeInTheDocument()
  })

  it("uses the fallback icon mapping for unknown categories", async () => {
    mockCategoriesApi({
      initialTree: [
        buildCategory({
          id: "category_mystery",
          name: "Mystery",
          sort_order: 10,
          children: [],
        }),
      ],
    })

    renderApp("/categories")

    expect(await screen.findByText("Mystery")).toBeInTheDocument()
    expect(screen.getAllByTestId("category-icon-category_mystery")[0]).toHaveAttribute(
      "data-icon-name",
      "fallback",
    )
  })

  it("creates a new root category from the page intro action", async () => {
    const { createSpy } = mockCategoriesApi()
    const user = userEvent.setup()

    renderApp("/categories")

    await screen.findByText("Food")
    await user.click(screen.getByRole("button", { name: "New category" }))
    await user.type(screen.getByLabelText("Name"), "Hobbies")
    await user.click(screen.getByRole("button", { name: "Create category" }))

    expect(await screen.findAllByText("Hobbies")).not.toHaveLength(0)
    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(
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

  it("creates a child category from the selected root panel", async () => {
    const { createSpy } = mockCategoriesApi()
    const user = userEvent.setup()

    renderApp("/categories")

    await screen.findByText("Groceries")
    await user.click(screen.getByRole("button", { name: "Add subcategory to Food" }))
    await user.type(screen.getByLabelText("Name"), "Board Games")
    await user.click(screen.getByRole("button", { name: "Create category" }))

    expect(await screen.findByText("Board Games")).toBeInTheDocument()
    expect(createSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        body: expect.objectContaining({
          name: "Board Games",
          parent_id: "category_food",
        }),
      }),
    )
  })

  it("edits a child category name", async () => {
    const { updateSpy } = mockCategoriesApi()
    const user = userEvent.setup()

    renderApp("/categories")

    await screen.findByText("Groceries")
    await user.click(screen.getByRole("button", { name: "Edit Groceries" }))
    await user.clear(screen.getByLabelText("Name"))
    await user.type(screen.getByLabelText("Name"), "Pantry")
    await user.click(screen.getByRole("button", { name: "Save category" }))

    expect(await screen.findByText("Pantry")).toBeInTheDocument()
    expect(updateSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        path: { category_id: "category_food_groceries" },
      }),
    )
  })

  it("reparents a child category to a different root", async () => {
    const { updateSpy } = mockCategoriesApi()
    const user = userEvent.setup()

    renderApp("/categories")

    await screen.findByText("Groceries")
    await user.click(screen.getByRole("button", { name: "Edit Groceries" }))
    await user.selectOptions(screen.getByLabelText("Parent category"), "category_housing")
    await user.click(screen.getByRole("button", { name: "Save category" }))

    await user.click(screen.getByRole("button", { name: "Housing 2 subcategories" }))

    expect(await screen.findByText("Groceries")).toBeInTheDocument()
    expect(updateSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        body: expect.objectContaining({
          parent_id: "category_housing",
        }),
        path: { category_id: "category_food_groceries" },
      }),
    )
  })

  it("converts a child category into a root category by clearing the parent", async () => {
    const user = userEvent.setup()

    mockCategoriesApi()
    renderApp("/categories")

    await screen.findByText("Groceries")
    await user.click(screen.getByRole("button", { name: "Edit Groceries" }))
    await user.selectOptions(screen.getByLabelText("Parent category"), "")
    await user.click(screen.getByRole("button", { name: "Save category" }))

    expect(await screen.findByText("No subcategories yet")).toBeInTheDocument()
    expect(screen.getAllByText("Groceries").length).toBeGreaterThan(0)
  })

  it("shows a duplicate-name error inline when the API rejects creation", async () => {
    mockCategoriesApi({
      onCreate: async () => {
        throw buildApiError(400, "category name must be unique within its sibling group")
      },
    })
    const user = userEvent.setup()

    renderApp("/categories")

    await screen.findByText("Groceries")
    await user.click(screen.getByRole("button", { name: "Add subcategory to Food" }))
    await user.type(screen.getByLabelText("Name"), "Restaurants")
    await user.click(screen.getByRole("button", { name: "Create category" }))

    expect(
      await screen.findByText("category name must be unique within its sibling group"),
    ).toBeInTheDocument()
  })

  it("shows an invalid-hierarchy error inline when reparenting a populated root", async () => {
    mockCategoriesApi({
      onUpdate: async ({ body }) => {
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
    await user.click(screen.getByRole("button", { name: "Save category" }))

    expect(
      await screen.findByText("category with children cannot become a child category"),
    ).toBeInTheDocument()
  })
})
