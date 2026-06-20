import { queryOptions } from "@tanstack/react-query"
import {
  SpendingCategoriesService,
  type CreateSpendingCategoryRequest,
  type SpendingCategoryResponse,
  type UpdateSpendingCategoryRequest,
} from "@/client"

const STALE_TIME_MS = 30_000

export const categoryKeys = {
  all: ["spending-categories"] as const,
  tree: () => [...categoryKeys.all, "tree"] as const,
}

export function categoriesTreeOptions() {
  return queryOptions({
    queryKey: categoryKeys.tree(),
    queryFn: () =>
      SpendingCategoriesService.spendingCategoriesListSpendingCategories<true>({
        throwOnError: true,
      }).then((result) => result.data),
    staleTime: STALE_TIME_MS,
  })
}

export function createCategory(
  payload: CreateSpendingCategoryRequest,
): Promise<SpendingCategoryResponse> {
  return SpendingCategoriesService.spendingCategoriesCreateSpendingCategory<true>({
    body: payload,
    throwOnError: true,
  }).then((result) => result.data)
}

export function updateCategory(
  categoryId: string,
  payload: UpdateSpendingCategoryRequest,
): Promise<SpendingCategoryResponse> {
  return SpendingCategoriesService.spendingCategoriesUpdateSpendingCategory<true>({
    body: payload,
    path: { category_id: categoryId },
    throwOnError: true,
  }).then((result) => result.data)
}

export function findCategoryInTree(
  categories: Array<SpendingCategoryResponse>,
  categoryId: string,
): SpendingCategoryResponse | undefined {
  for (const category of categories) {
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

export function upsertCategoryTree(
  categories: Array<SpendingCategoryResponse> | undefined,
  incoming: SpendingCategoryResponse,
): Array<SpendingCategoryResponse> {
  const currentCategories = categories ?? []
  const existing = findCategoryInTree(currentCategories, incoming.id)
  const nextCategory: SpendingCategoryResponse = {
    ...incoming,
    children: existing?.children ?? incoming.children ?? [],
  }

  const cleaned = removeCategoryFromTree(currentCategories, incoming.id)

  if (nextCategory.parent_id === null) {
    return sortCategoryTree([...cleaned, nextCategory])
  }

  return sortCategoryTree(
    cleaned.map((root) =>
      root.id === nextCategory.parent_id
        ? {
            ...root,
            children: sortCategorySiblings([...(root.children ?? []), nextCategory]),
          }
        : root,
    ),
  )
}

function removeCategoryFromTree(
  categories: Array<SpendingCategoryResponse>,
  categoryId: string,
): Array<SpendingCategoryResponse> {
  return categories
    .filter((category) => category.id !== categoryId)
    .map((category) => ({
      ...category,
      children: (category.children ?? []).filter((child) => child.id !== categoryId),
    }))
}

function sortCategoryTree(
  categories: Array<SpendingCategoryResponse>,
): Array<SpendingCategoryResponse> {
  return sortCategorySiblings(categories).map((category) => ({
    ...category,
    children: sortCategorySiblings(category.children ?? []),
  }))
}

function sortCategorySiblings(
  categories: Array<SpendingCategoryResponse>,
): Array<SpendingCategoryResponse> {
  return [...categories].sort((left, right) => {
    if (left.sort_order !== right.sort_order) {
      return left.sort_order - right.sort_order
    }

    return left.name.localeCompare(right.name, undefined, { sensitivity: "base" })
  })
}
