import { useEffect, useId, useState } from "react"
import type { SpendingCategoryResponse } from "@/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { cn } from "@/lib/utils"

const selectClassName =
  "border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-sm shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]"

export type CategoryFormMode =
  | { kind: "create-root" }
  | { kind: "create-child"; parentId: string }
  | { kind: "edit"; categoryId: string }

export type CategoryFormValues = {
  name: string
  parentId: string | null
  sortOrder: number
}

export function CategoryFormSheet({
  currentCategory,
  errorMessage,
  isPending,
  mode,
  onOpenChange,
  onSubmit,
  open,
  rootCategories,
}: {
  currentCategory?: SpendingCategoryResponse
  errorMessage?: string
  isPending: boolean
  mode: CategoryFormMode | null
  onOpenChange: (open: boolean) => void
  onSubmit: (values: CategoryFormValues) => Promise<void>
  open: boolean
  rootCategories: Array<SpendingCategoryResponse>
}) {
  const nameId = useId()
  const parentId = useId()
  const [name, setName] = useState("")
  const [selectedParentId, setSelectedParentId] = useState("")
  const [sortOrder, setSortOrder] = useState("0")

  useEffect(() => {
    if (!open || !mode) {
      return
    }

    if (mode.kind === "create-root") {
      setName("")
      setSelectedParentId("")
      setSortOrder("0")
      return
    }

    if (mode.kind === "create-child") {
      setName("")
      setSelectedParentId(mode.parentId)
      setSortOrder("0")
      return
    }

    if (currentCategory) {
      setName(currentCategory.name)
      setSelectedParentId(currentCategory.parent_id ?? "")
      setSortOrder(String(currentCategory.sort_order))
    }
  }, [currentCategory, mode, open])

  if (!mode) {
    return null
  }

  const availableRoots = rootCategories.filter((category) => {
    if (mode.kind !== "edit") {
      return true
    }

    return category.id !== mode.categoryId
  })

  const title =
    mode.kind === "create-root"
      ? "Create root category"
      : mode.kind === "create-child"
        ? "Create subcategory"
        : "Edit category"

  const description =
    mode.kind === "create-root"
      ? "Add a new top-level spending category."
      : mode.kind === "create-child"
        ? "Add a category underneath the selected root category."
        : "Update the category name or parent placement."

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    await onSubmit({
      name: name.trim(),
      parentId: selectedParentId || null,
      sortOrder: Number.parseInt(sortOrder, 10) || 0,
    })
  }

  return (
    <Sheet onOpenChange={onOpenChange} open={open}>
      <SheetContent className="w-full sm:max-w-lg" side="right">
        <SheetHeader className="border-b border-border/70 pb-4">
          <SheetTitle>{title}</SheetTitle>
          <SheetDescription>{description}</SheetDescription>
        </SheetHeader>
        <form className="flex flex-1 flex-col" onSubmit={handleSubmit}>
          <div className="grid gap-5 px-4 py-5">
            <div className="grid gap-2">
              <Label htmlFor={nameId}>Name</Label>
              <Input
                id={nameId}
                onChange={(event) => setName(event.target.value)}
                placeholder="Groceries, Utilities, Streaming"
                required
                value={name}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor={parentId}>Parent category</Label>
              <select
                className={cn(selectClassName, "dark:bg-input/30")}
                id={parentId}
                onChange={(event) => setSelectedParentId(event.target.value)}
                value={selectedParentId}
              >
                <option value="">No parent</option>
                {availableRoots.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
              <p className="text-sm text-muted-foreground">
                Only root categories can be selected as parents.
              </p>
            </div>

            {errorMessage ? (
              <div className="rounded-xl border border-destructive/30 bg-destructive/8 px-4 py-3 text-sm text-destructive">
                {errorMessage}
              </div>
            ) : null}
          </div>

          <SheetFooter className="border-t border-border/70">
            <Button onClick={() => onOpenChange(false)} type="button" variant="outline">
              Cancel
            </Button>
            <Button disabled={isPending || name.trim().length === 0} type="submit">
              {isPending
                ? mode.kind === "edit"
                  ? "Saving..."
                  : "Creating..."
                : mode.kind === "edit"
                  ? "Save category"
                  : "Create category"}
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  )
}
