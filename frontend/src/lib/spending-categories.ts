import { queryOptions } from "@tanstack/react-query"
import {
  SpendingCategoriesService,
  type CreateSpendingCategoryRequest,
  type SpendingCategoryResponse,
  type UpdateSpendingCategoryRequest,
} from "@/client"

const STALE_TIME_MS = 30_000

export const spendingCategoryKeys = {
  all: ["spending-categories"] as const,
  tree: () => [...spendingCategoryKeys.all, "tree"] as const,
}

export function spendingCategoriesTreeOptions() {
  return queryOptions({
    queryKey: spendingCategoryKeys.tree(),
    queryFn: () =>
      SpendingCategoriesService.spendingCategoriesListSpendingCategories<true>({
        throwOnError: true,
      }).then((result) => result.data),
    staleTime: STALE_TIME_MS,
  })
}

export function createSpendingCategory(
  payload: CreateSpendingCategoryRequest,
): Promise<SpendingCategoryResponse> {
  return SpendingCategoriesService.spendingCategoriesCreateSpendingCategory<true>({
    body: payload,
    throwOnError: true,
  }).then((result) => result.data)
}

export function updateSpendingCategory(
  categoryId: string,
  payload: UpdateSpendingCategoryRequest,
): Promise<SpendingCategoryResponse> {
  return SpendingCategoriesService.spendingCategoriesUpdateSpendingCategory<true>({
    body: payload,
    path: { category_id: categoryId },
    throwOnError: true,
  }).then((result) => result.data)
}
