import type { ReactNode } from "react"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
} from "@/components/ui/card"
import { cn } from "@/lib/utils"

export function AccountPageIntro({
  eyebrow,
  title,
  description,
  action,
  className,
}: {
  eyebrow: string
  title: string
  description: string
  action?: ReactNode
  className?: string
}) {
  return (
    <section
      className={cn(
        "grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-start",
        className,
      )}
    >
      <div className="max-w-3xl">
        <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">
          {eyebrow}
        </p>
        <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
      </div>
      {action ? <div className="lg:justify-self-end">{action}</div> : null}
    </section>
  )
}

export function AccountSplitLayout({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn("grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]", className)}>
      {children}
    </div>
  )
}

export function AccountSectionStack({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <div className={cn("grid gap-6", className)}>{children}</div>
}

export function AccountFieldGrid({
  children,
  columns = "three",
  className,
}: {
  children: ReactNode
  columns?: "two" | "three"
  className?: string
}) {
  return (
    <div
      className={cn(
        "grid gap-4",
        columns === "two"
          ? "md:grid-cols-[minmax(0,1fr)_220px]"
          : "md:grid-cols-3",
        className,
      )}
    >
      {children}
    </div>
  )
}

export function AccountFieldStack({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <div className={cn("grid content-start gap-2", className)}>{children}</div>
}

export function AccountSectionCard({
  title,
  description,
  children,
  footer,
  className,
  contentClassName,
}: {
  title: string
  description?: string
  children: ReactNode
  footer?: ReactNode
  className?: string
  contentClassName?: string
}) {
  return (
    <Card className={className}>
      <CardHeader>
        <h3 className="leading-none font-semibold">{title}</h3>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent className={contentClassName}>{children}</CardContent>
      {footer ? <CardFooter className="border-t border-border/70">{footer}</CardFooter> : null}
    </Card>
  )
}

export function AccountFactList({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <dl className={cn("grid gap-3 text-sm", className)}>{children}</dl>
}

export function AccountFactRow({
  label,
  value,
}: {
  label: string
  value: ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right font-medium">{value}</dd>
    </div>
  )
}
