import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Plus } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import type {
  CreateSpendingCategoryRequest,
  SpendingCategoryResponse,
  UpdateSpendingCategoryRequest,
} from "@/client"
import {
  CategoryDetailPanel,
} from "@/components/categories/category-detail-panel"
import {
  CategoryFormSheet,
  type CategoryFormMode,
  type CategoryFormValues,
} from "@/components/categories/category-form-sheet"
import { CategoryRootGallery } from "@/components/categories/category-root-gallery"
import { PageIntro, SectionStack, SplitLayout } from "@/components/layout/page-layout"
import { Button } from "@/components/ui/button"
import { getApiErrorMessage } from "@/lib/api-errors"
import {
  categoriesTreeOptions,
  categoryKeys,
  createCategory,
  findCategoryInTree,
  updateCategory,
  upsertCategoryTree,
} from "@/lib/categories"

export function CategoriesRoute() {
  const queryClient = useQueryClient()
  const categoriesQuery = useQuery(categoriesTreeOptions())
  const [selectedRootId, setSelectedRootId] = useState<string>()
  const [sheetMode, setSheetMode] = useState<CategoryFormMode | null>(null)
  const [errorMessage, setErrorMessage] = useState<string>()

  const rootCategories = categoriesQuery.data ?? []
  const currentCategory =
    sheetMode?.kind === "edit" ? findCategoryInTree(rootCategories, sheetMode.categoryId) : undefined

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

  const createCategoryMutation = useMutation({
    mutationFn: (payload: CreateSpendingCategoryRequest) => createCategory(payload),
    onSuccess: async (category) => {
      queryClient.setQueryData<Array<SpendingCategoryResponse>>(
        categoryKeys.tree(),
        (categories) => upsertCategoryTree(categories, category),
      )
      await queryClient.invalidateQueries({ queryKey: categoryKeys.tree() })
      setErrorMessage(undefined)
      setSheetMode(null)
      setSelectedRootId(category.parent_id ?? category.id)
    },
  })

  const updateCategoryMutation = useMutation({
    mutationFn: ({
      categoryId,
      payload,
    }: {
      categoryId: string
      payload: UpdateSpendingCategoryRequest
    }) => updateCategory(categoryId, payload),
    onSuccess: async (category) => {
      queryClient.setQueryData<Array<SpendingCategoryResponse>>(
        categoryKeys.tree(),
        (categories) => upsertCategoryTree(categories, category),
      )
      await queryClient.invalidateQueries({ queryKey: categoryKeys.tree() })
      setErrorMessage(undefined)
      setSheetMode(null)
      if (category.parent_id === null) {
        setSelectedRootId(category.id)
      } else if (selectedRootId === category.id) {
        setSelectedRootId(category.parent_id)
      }
    },
  })

  const isPending = createCategoryMutation.isPending || updateCategoryMutation.isPending

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
        await updateCategoryMutation.mutateAsync({
          categoryId: sheetMode.categoryId,
          payload: {
            name: values.name,
            parent_id: values.parentId,
            sort_order: values.sortOrder,
          },
        })
        return
      }

      await createCategoryMutation.mutateAsync({
        name: values.name,
        parent_id: values.parentId,
        sort_order: values.sortOrder,
      })
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error))
    }
  }

  if (categoriesQuery.isLoading) {
    return (
      <section className="rounded-[2rem] border bg-card p-8 shadow-sm">
        <p className="text-lg font-semibold">Loading categories...</p>
      </section>
    )
  }

  if (categoriesQuery.isError) {
    return (
      <section className="rounded-[2rem] border bg-card p-8 shadow-sm">
        <p className="text-lg font-semibold">Unable to load categories.</p>
        <p className="mt-2 text-sm text-destructive">
          {getApiErrorMessage(categoriesQuery.error)}
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
              New category
            </Button>
          }
          description="Organize the default spending tree, add new categories, and keep child groups tidy for future expense classification."
          eyebrow="Categories"
          title="Spending categories"
        />

        {rootCategories.length === 0 ? (
          <section className="rounded-[2rem] border border-dashed bg-card/70 px-8 py-12 text-center shadow-sm">
            <p className="text-lg font-semibold">No categories yet.</p>
            <p className="mt-2 text-sm text-muted-foreground">
              Create the first top-level category to start shaping your spending taxonomy.
            </p>
            <Button className="mt-6 rounded-full px-5" onClick={openCreateRoot}>
              <Plus className="size-4" />
              Create first category
            </Button>
          </section>
        ) : (
          <SplitLayout className="items-start">
            <CategoryRootGallery
              onEdit={openEdit}
              onSelect={setSelectedRootId}
              rootCategories={rootCategories}
              selectedCategoryId={selectedRoot?.id}
            />
            <CategoryDetailPanel
              onCreateChild={openCreateChild}
              onEditChild={openEdit}
              onEditRoot={openEdit}
              selectedRoot={selectedRoot}
            />
          </SplitLayout>
        )}
      </SectionStack>

      <CategoryFormSheet
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
