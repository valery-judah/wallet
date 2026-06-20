import { PencilLine, Plus } from "lucide-react"
import type { SpendingCategoryResponse } from "@/client"
import { CategoryIcon, formatCategoryCount } from "@/components/categories/category-appearance"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function CategoryDetailPanel({
  selectedRoot,
  onCreateChild,
  onEditChild,
  onEditRoot,
}: {
  selectedRoot?: SpendingCategoryResponse
  onCreateChild: (categoryId: string) => void
  onEditChild: (categoryId: string) => void
  onEditRoot: (categoryId: string) => void
}) {
  if (!selectedRoot) {
    return (
      <section className="rounded-[2rem] border border-dashed border-border/70 bg-card/60 p-8 text-center shadow-sm">
        <p className="text-lg font-semibold">Choose a category</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Select a root category to inspect and manage its child categories.
        </p>
      </section>
    )
  }

  const children = selectedRoot.children ?? []

  return (
    <section className="overflow-hidden rounded-[2rem] border border-border/70 bg-gradient-to-br from-card via-card to-muted/20 shadow-sm dark:border-white/8 dark:from-[#141821] dark:via-[#161b24] dark:to-[#10141c]">
      <div className="border-b border-border/70 px-6 py-6 dark:border-white/7">
        <div className="flex items-start justify-between gap-4">
          <div className="flex min-w-0 items-start gap-4">
            <div className="flex size-16 shrink-0 items-center justify-center rounded-[1.4rem] bg-foreground/[0.05] text-foreground/80 dark:bg-white/[0.05] dark:text-slate-100">
              <CategoryIcon category={selectedRoot} className="size-8 stroke-[1.9]" />
            </div>
            <div className="min-w-0">
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">
                Root category
              </p>
              <h3 className="mt-2 truncate text-2xl font-semibold tracking-[-0.03em]">
                {selectedRoot.name}
              </h3>
              <p className="mt-2 text-sm text-muted-foreground">
                {formatCategoryCount(children.length)}. Categories only support one child level.
              </p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button
              aria-label={`Edit ${selectedRoot.name}`}
              className="rounded-full"
              onClick={() => onEditRoot(selectedRoot.id)}
              size="sm"
              type="button"
              variant="outline"
            >
              <PencilLine className="size-4" />
              Edit
            </Button>
            <Button
              aria-label={`Add subcategory to ${selectedRoot.name}`}
              className="rounded-full"
              onClick={() => onCreateChild(selectedRoot.id)}
              size="sm"
              type="button"
            >
              <Plus className="size-4" />
              Add subcategory
            </Button>
          </div>
        </div>
      </div>

      <div className="px-6 py-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold">Subcategories</p>
            <p className="text-sm text-muted-foreground">
              Rename and reorganize the categories nested under {selectedRoot.name}.
            </p>
          </div>
        </div>

        {children.length === 0 ? (
          <div className="rounded-[1.5rem] border border-dashed border-border/70 bg-background/60 px-5 py-8 text-center dark:border-white/10 dark:bg-white/[0.03]">
            <p className="font-medium">No subcategories yet.</p>
            <p className="mt-2 text-sm text-muted-foreground">
              Add one to keep future spending classification organized.
            </p>
          </div>
        ) : (
          <ul className="grid gap-3">
            {children.map((child) => (
              <li
                className={cn(
                  "flex items-center justify-between gap-4 rounded-[1.4rem] border px-4 py-4",
                  "border-border/70 bg-background/75 dark:border-white/8 dark:bg-[#1a1f28]",
                )}
                key={child.id}
              >
                <div className="flex min-w-0 items-center gap-3">
                  <div className="flex size-11 shrink-0 items-center justify-center rounded-[1rem] bg-muted text-muted-foreground dark:bg-white/[0.05] dark:text-slate-200">
                    <CategoryIcon category={child} className="size-5 stroke-[1.9]" />
                  </div>
                  <p className="min-w-0 truncate font-medium">{child.name}</p>
                </div>
                <Button
                  aria-label={`Edit ${child.name}`}
                  className="rounded-full"
                  onClick={() => onEditChild(child.id)}
                  size="sm"
                  type="button"
                  variant="ghost"
                >
                  <PencilLine className="size-4" />
                  Edit
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
