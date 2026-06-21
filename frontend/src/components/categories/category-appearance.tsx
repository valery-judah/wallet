import type { ComponentType } from "react"
import {
  CarFront,
  CircleEllipsis,
  Film,
  Gift,
  GraduationCap,
  House,
  Landmark,
  PawPrint,
  Pill,
  Plane,
  Receipt,
  ShoppingBag,
  Sparkles,
  Tag,
  UtensilsCrossed,
} from "lucide-react"
import type { CategoryTreeNode } from "@/lib/categories"
import { cn } from "@/lib/utils"

type CategoryIconComponent = ComponentType<{ className?: string }>

const ICONS_BY_ID: Record<string, CategoryIconComponent> = {
  category_education: GraduationCap,
  category_entertainment: Film,
  category_fees: Receipt,
  category_food: UtensilsCrossed,
  category_gifts_and_donations: Gift,
  category_health: Pill,
  category_housing: House,
  category_other: CircleEllipsis,
  category_personal: Sparkles,
  category_pets: PawPrint,
  category_shopping: ShoppingBag,
  category_taxes: Landmark,
  category_transport: CarFront,
  category_travel: Plane,
}

const ICONS_BY_NORMALIZED_NAME: Record<string, CategoryIconComponent> = {
  education: GraduationCap,
  entertainment: Film,
  fees: Receipt,
  food: UtensilsCrossed,
  "gifts & donations": Gift,
  health: Pill,
  housing: House,
  other: CircleEllipsis,
  personal: Sparkles,
  pets: PawPrint,
  shopping: ShoppingBag,
  taxes: Landmark,
  transport: CarFront,
  travel: Plane,
}

export function getCategoryIconComponent(
  category: CategoryTreeNode,
): CategoryIconComponent {
  return (
    ICONS_BY_ID[category.id] ??
    ICONS_BY_NORMALIZED_NAME[category.name.trim().toLocaleLowerCase()] ??
    Tag
  )
}

export function getCategoryIconName(category: CategoryTreeNode): string {
  if (ICONS_BY_ID[category.id]) {
    return category.id
  }

  const normalizedName = category.name.trim().toLocaleLowerCase()
  if (ICONS_BY_NORMALIZED_NAME[normalizedName]) {
    return normalizedName
  }

  return "fallback"
}

export function CategoryIcon({
  category,
  className,
}: {
  category: CategoryTreeNode
  className?: string
}) {
  const Icon = getCategoryIconComponent(category)

  return (
    <Icon
      className={cn("size-5", className)}
      data-icon-name={getCategoryIconName(category)}
      data-testid={`category-icon-${category.id}`}
    />
  )
}

export function formatCategoryCount(count: number): string {
  if (count === 0) {
    return "No subcategories yet"
  }

  if (count === 1) {
    return "1 subcategory"
  }

  return `${count} subcategories`
}
