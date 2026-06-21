import { queryOptions } from "@tanstack/react-query"
import {
  IncomeCategoriesService,
  type CreateIncomeCategoryRequest,
  type IncomeCategoryResponse,
  type UpdateIncomeCategoryRequest,
} from "@/client"

const STALE_TIME_MS = 30_000

export const incomeCategoryKeys = {
  all: ["income-categories"] as const,
  tree: () => [...incomeCategoryKeys.all, "tree"] as const,
}

export function incomeCategoriesTreeOptions() {
  return queryOptions({
    queryKey: incomeCategoryKeys.tree(),
    queryFn: () =>
      IncomeCategoriesService.incomeCategoriesListIncomeCategories<true>({
        throwOnError: true,
      }).then((result) => result.data),
    staleTime: STALE_TIME_MS,
  })
}

export function createIncomeCategory(
  payload: CreateIncomeCategoryRequest,
): Promise<IncomeCategoryResponse> {
  return IncomeCategoriesService.incomeCategoriesCreateIncomeCategory<true>({
    body: payload,
    throwOnError: true,
  }).then((result) => result.data)
}

export function updateIncomeCategory(
  categoryId: string,
  payload: UpdateIncomeCategoryRequest,
): Promise<IncomeCategoryResponse> {
  return IncomeCategoriesService.incomeCategoriesUpdateIncomeCategory<true>({
    body: payload,
    path: { category_id: categoryId },
    throwOnError: true,
  }).then((result) => result.data)
}
