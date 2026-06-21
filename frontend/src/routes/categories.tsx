import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Plus } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import type {
  CreateIncomeCategoryRequest,
  CreateSpendingCategoryRequest,
  IncomeCategoryResponse,
  SpendingCategoryResponse,
  UpdateIncomeCategoryRequest,
  UpdateSpendingCategoryRequest,
} from "@/client"
import { CategoryDetailPanel } from "@/components/categories/category-detail-panel"
import {
  CategoryFormSheet,
  type CategoryFormMode,
  type CategoryFormValues,
} from "@/components/categories/category-form-sheet"
import { CategoryRootGallery } from "@/components/categories/category-root-gallery"
import { PageIntro, SectionStack, SplitLayout } from "@/components/layout/page-layout"
import { Button } from "@/components/ui/button"
import { getApiErrorMessage } from "@/lib/api-errors"
import { findCategoryInTree, upsertCategoryTree } from "@/lib/categories"
import {
  createIncomeCategory,
  incomeCategoriesTreeOptions,
  incomeCategoryKeys,
  updateIncomeCategory,
} from "@/lib/income-categories"
import {
  createSpendingCategory,
  spendingCategoriesTreeOptions,
  spendingCategoryKeys,
  updateSpendingCategory,
} from "@/lib/spending-categories"

type CategoryFamily = "spending" | "income"

export function CategoriesRoute() {
  const queryClient = useQueryClient()
  const spendingCategoriesQuery = useQuery(spendingCategoriesTreeOptions())
  const incomeCategoriesQuery = useQuery(incomeCategoriesTreeOptions())
  const [family, setFamily] = useState<CategoryFamily>("spending")
  const [selectedRootId, setSelectedRootId] = useState<string>()
  const [sheetMode, setSheetMode] = useState<CategoryFormMode | null>(null)
  const [errorMessage, setErrorMessage] = useState<string>()

  const rootCategories =
    family === "spending" ? spendingCategoriesQuery.data ?? [] : incomeCategoriesQuery.data ?? []
  const currentCategory =
    sheetMode?.kind === "edit" ? findCategoryInTree(rootCategories, sheetMode.categoryId) : undefined
  const categoryLabel = family === "spending" ? "Spending" : "Income"

  const selectedRoot = useMemo(
    () => rootCategories.find((category) => category.id === selectedRootId),
    [rootCategories, selectedRootId],
  )

  useEffect(() => {
    if (rootCategories.length === 0) {
      if (selectedRootId !== undefined) {
        setSelectedRootId(undefined)
      }
      return
    }

    if (!selectedRootId || !rootCategories.some((category) => category.id === selectedRootId)) {
      setSelectedRootId(rootCategories[0].id)
    }
  }, [rootCategories, selectedRootId])

  useEffect(() => {
    if (sheetMode?.kind === "edit" && !currentCategory) {
      setSheetMode(null)
    }
  }, [currentCategory, sheetMode])

  useEffect(() => {
    setErrorMessage(undefined)
    setSheetMode(null)
    setSelectedRootId(undefined)
  }, [family])

  const createSpendingCategoryMutation = useMutation({
    mutationFn: (payload: CreateSpendingCategoryRequest) => createSpendingCategory(payload),
    onSuccess: async (category) => {
      queryClient.setQueryData<Array<SpendingCategoryResponse>>(
        spendingCategoryKeys.tree(),
        (categories) => upsertCategoryTree(categories, category),
      )
      await queryClient.invalidateQueries({ queryKey: spendingCategoryKeys.tree() })
      setErrorMessage(undefined)
      setSheetMode(null)
      setSelectedRootId(category.parent_id ?? category.id)
    },
  })

  const updateSpendingCategoryMutation = useMutation({
    mutationFn: ({
      categoryId,
      payload,
    }: {
      categoryId: string
      payload: UpdateSpendingCategoryRequest
    }) => updateSpendingCategory(categoryId, payload),
    onSuccess: async (category) => {
      queryClient.setQueryData<Array<SpendingCategoryResponse>>(
        spendingCategoryKeys.tree(),
        (categories) => upsertCategoryTree(categories, category),
      )
      await queryClient.invalidateQueries({ queryKey: spendingCategoryKeys.tree() })
      setErrorMessage(undefined)
      setSheetMode(null)
      if (category.parent_id === null) {
        setSelectedRootId(category.id)
      } else if (selectedRootId === category.id) {
        setSelectedRootId(category.parent_id)
      }
    },
  })

  const createIncomeCategoryMutation = useMutation({
    mutationFn: (payload: CreateIncomeCategoryRequest) => createIncomeCategory(payload),
    onSuccess: async (category) => {
      queryClient.setQueryData<Array<IncomeCategoryResponse>>(
        incomeCategoryKeys.tree(),
        (categories) => upsertCategoryTree(categories, category),
      )
      await queryClient.invalidateQueries({ queryKey: incomeCategoryKeys.tree() })
      setErrorMessage(undefined)
      setSheetMode(null)
      setSelectedRootId(category.parent_id ?? category.id)
    },
  })

  const updateIncomeCategoryMutation = useMutation({
    mutationFn: ({
      categoryId,
      payload,
    }: {
      categoryId: string
      payload: UpdateIncomeCategoryRequest
    }) => updateIncomeCategory(categoryId, payload),
    onSuccess: async (category) => {
      queryClient.setQueryData<Array<IncomeCategoryResponse>>(
        incomeCategoryKeys.tree(),
        (categories) => upsertCategoryTree(categories, category),
      )
      await queryClient.invalidateQueries({ queryKey: incomeCategoryKeys.tree() })
      setErrorMessage(undefined)
      setSheetMode(null)
      if (category.parent_id === null) {
        setSelectedRootId(category.id)
      } else if (selectedRootId === category.id) {
        setSelectedRootId(category.parent_id)
      }
    },
  })

  const isPending =
    createSpendingCategoryMutation.isPending ||
    updateSpendingCategoryMutation.isPending ||
    createIncomeCategoryMutation.isPending ||
    updateIncomeCategoryMutation.isPending

  function openCreateRoot() {
    setErrorMessage(undefined)
    setSheetMode({ kind: "create-root" })
  }

  function openCreateChild(parentId: string) {
    setErrorMessage(undefined)
    setSheetMode({ kind: "create-child", parentId })
  }

  function openEdit(categoryId: string) {
    setErrorMessage(undefined)
    setSheetMode({ kind: "edit", categoryId })
  }

  function handleOpenChange(open: boolean) {
    if (open) {
      return
    }

    setErrorMessage(undefined)
    setSheetMode(null)
  }

  async function handleSubmit(values: CategoryFormValues) {
    setErrorMessage(undefined)

    try {
      if (sheetMode?.kind === "edit") {
        if (family === "spending") {
          await updateSpendingCategoryMutation.mutateAsync({
            categoryId: sheetMode.categoryId,
            payload: {
              name: values.name,
              parent_id: values.parentId,
              sort_order: values.sortOrder,
            },
          })
        } else {
          await updateIncomeCategoryMutation.mutateAsync({
            categoryId: sheetMode.categoryId,
            payload: {
              name: values.name,
              parent_id: values.parentId,
              sort_order: values.sortOrder,
            },
          })
        }
        return
      }

      if (family === "spending") {
        await createSpendingCategoryMutation.mutateAsync({
          name: values.name,
          parent_id: values.parentId,
          sort_order: values.sortOrder,
        })
      } else {
        await createIncomeCategoryMutation.mutateAsync({
          name: values.name,
          parent_id: values.parentId,
          sort_order: values.sortOrder,
        })
      }
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error))
    }
  }

  if (spendingCategoriesQuery.isLoading || incomeCategoriesQuery.isLoading) {
    return (
      <section className="rounded-[2rem] border bg-card p-8 shadow-sm">
        <p className="text-lg font-semibold">Loading categories...</p>
      </section>
    )
  }

  const activeError = family === "spending" ? spendingCategoriesQuery.error : incomeCategoriesQuery.error
  if (spendingCategoriesQuery.isError || incomeCategoriesQuery.isError) {
    return (
      <section className="rounded-[2rem] border bg-card p-8 shadow-sm">
        <p className="text-lg font-semibold">Unable to load categories.</p>
        <p className="mt-2 text-sm text-destructive">
          {getApiErrorMessage(activeError)}
        </p>
      </section>
    )
  }

  return (
    <>
      <SectionStack>
        <PageIntro
          action={
            <Button className="h-10 rounded-full px-5 text-sm font-semibold" onClick={openCreateRoot}>
              <Plus className="size-4" />
              New {categoryLabel.toLowerCase()} category
            </Button>
          }
          description="Manage separate spending and income category trees without mixing the two classification families."
          eyebrow="Categories"
          title="Category trees"
        />

        <div className="flex flex-wrap gap-2">
          {(
            [
              ["spending", "Spending"],
              ["income", "Income"],
            ] as const
          ).map(([value, label]) => (
            <button
              aria-pressed={family === value}
              className={
                family === value
                  ? "rounded-full border border-primary/40 bg-primary/10 px-4 py-2 text-sm font-semibold"
                  : "rounded-full border border-border/70 bg-background/70 px-4 py-2 text-sm font-semibold"
              }
              key={value}
              onClick={() => setFamily(value)}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>

        {rootCategories.length === 0 ? (
          <section className="rounded-[2rem] border border-dashed bg-card/70 px-8 py-12 text-center shadow-sm">
            <p className="text-lg font-semibold">No categories yet.</p>
            <p className="mt-2 text-sm text-muted-foreground">
              Create the first top-level {categoryLabel.toLowerCase()} category to start shaping this tree.
            </p>
            <Button className="mt-6 rounded-full px-5" onClick={openCreateRoot}>
              <Plus className="size-4" />
              Create first {categoryLabel.toLowerCase()} category
            </Button>
          </section>
        ) : (
          <SplitLayout className="items-start">
            <CategoryRootGallery
              categoryLabel={categoryLabel}
              onEdit={openEdit}
              onSelect={setSelectedRootId}
              rootCategories={rootCategories}
              selectedCategoryId={selectedRoot?.id}
            />
            <CategoryDetailPanel
              categoryLabel={categoryLabel}
              onCreateChild={openCreateChild}
              onEditChild={openEdit}
              onEditRoot={openEdit}
              selectedRoot={selectedRoot}
            />
          </SplitLayout>
        )}
      </SectionStack>

      <CategoryFormSheet
        categoryLabel={categoryLabel}
        currentCategory={currentCategory}
        errorMessage={errorMessage}
        isPending={isPending}
        mode={sheetMode}
        onOpenChange={handleOpenChange}
        onSubmit={handleSubmit}
        open={sheetMode !== null}
        rootCategories={rootCategories}
      />
    </>
  )
}
