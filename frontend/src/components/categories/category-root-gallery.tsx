import { PencilLine } from "lucide-react"
import { CategoryIcon, formatCategoryCount } from "@/components/categories/category-appearance"
import { Button } from "@/components/ui/button"
import type { CategoryTreeNode } from "@/lib/categories"
import { cn } from "@/lib/utils"

export function CategoryRootGallery({
  categoryLabel,
  rootCategories,
  selectedCategoryId,
  onEdit,
  onSelect,
}: {
  categoryLabel: string
  rootCategories: Array<CategoryTreeNode>
  selectedCategoryId?: string
  onEdit: (categoryId: string) => void
  onSelect: (categoryId: string) => void
}) {
  return (
    <section className="overflow-hidden rounded-[2rem] border border-border/70 bg-gradient-to-br from-card via-card to-muted/30 p-5 shadow-sm dark:border-white/8 dark:from-[#13161d] dark:via-[#151922] dark:to-[#11141a]">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">Top-level {categoryLabel.toLowerCase()} categories</p>
          <p className="text-sm text-muted-foreground">
            Pick a root category to manage its child categories.
          </p>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {rootCategories.map((category) => {
          const isSelected = category.id === selectedCategoryId

          return (
            <article
              className={cn(
                "group relative overflow-hidden rounded-[1.6rem] border transition",
                "border-border/80 bg-background/80 dark:border-white/7 dark:bg-[#171b24]",
                "hover:border-border hover:bg-accent/15 dark:hover:border-white/14 dark:hover:bg-[#1a1f29]",
                isSelected &&
                  "border-primary/40 bg-primary/5 shadow-[0_0_0_1px_rgba(17,184,195,0.14)] dark:border-white/15 dark:bg-[#1d2330]",
              )}
              key={category.id}
            >
              <Button
                aria-pressed={isSelected}
                className="absolute top-3 right-3 z-10 rounded-full border border-border/70 bg-background/75 text-muted-foreground shadow-none hover:bg-background dark:border-white/10 dark:bg-white/6 dark:text-slate-200 dark:hover:bg-white/10"
                onClick={() => onEdit(category.id)}
                size="icon-sm"
                type="button"
                variant="ghost"
              >
                <PencilLine aria-hidden="true" className="size-4" />
                <span className="sr-only">Edit {category.name}</span>
              </Button>
              <button
                className="flex w-full flex-col items-center px-4 py-5 text-center outline-hidden focus-visible:ring-2 focus-visible:ring-primary/40"
                onClick={() => onSelect(category.id)}
                type="button"
              >
                <div
                  className={cn(
                    "mb-4 flex size-20 items-center justify-center rounded-[1.5rem] border",
                    "border-transparent bg-foreground/[0.04] text-foreground/75 dark:bg-white/[0.04] dark:text-slate-200",
                    isSelected &&
                      "bg-primary/8 text-primary dark:bg-white/[0.07] dark:text-white",
                  )}
                >
                  <CategoryIcon category={category} className="size-8 stroke-[1.8]" />
                </div>
                <h3 className="text-xl font-semibold tracking-[-0.03em]">{category.name}</h3>
                <p className="mt-1.5 text-sm text-muted-foreground">
                  {formatCategoryCount(category.children?.length ?? 0)}
                </p>
              </button>
            </article>
          )
        })}
      </div>
    </section>
  )
}
