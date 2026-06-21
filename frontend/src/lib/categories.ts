export type CategoryTreeNode = {
  id: string
  name: string
  parent_id: string | null
  icon?: string | null
  color?: string | null
  sort_order: number
  children?: Array<CategoryTreeNode>
}

export function findCategoryInTree<T extends CategoryTreeNode>(
  categories: Array<T>,
  categoryId: string,
): T | undefined {
  for (const category of categories) {
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

export function upsertCategoryTree<T extends CategoryTreeNode>(
  categories: Array<T> | undefined,
  incoming: T,
): Array<T> {
  const currentCategories = categories ?? []
  const existing = findCategoryInTree(currentCategories, incoming.id)
  const nextCategory: T = {
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

function removeCategoryFromTree<T extends CategoryTreeNode>(
  categories: Array<T>,
  categoryId: string,
): Array<T> {
  return categories
    .filter((category) => category.id !== categoryId)
    .map((category) => ({
      ...category,
      children: (category.children ?? []).filter((child) => child.id !== categoryId),
    }))
}

function sortCategoryTree<T extends CategoryTreeNode>(categories: Array<T>): Array<T> {
  return sortCategorySiblings(categories).map((category) => ({
    ...category,
    children: sortCategorySiblings(category.children ?? []),
  }))
}

function sortCategorySiblings<T extends CategoryTreeNode>(categories: Array<T>): Array<T> {
  return [...categories].sort((left, right) => {
    if (left.sort_order !== right.sort_order) {
      return left.sort_order - right.sort_order
    }

    return left.name.localeCompare(right.name, undefined, { sensitivity: "base" })
  })
}
