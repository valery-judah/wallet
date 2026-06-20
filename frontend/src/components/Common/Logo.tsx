import { Link } from "@tanstack/react-router"

import { useTheme } from "@/components/theme-provider"
import { cn } from "@/lib/utils"

interface LogoProps {
  variant?: "full" | "icon" | "responsive"
  className?: string
  asLink?: boolean
}

export function Logo({
  variant = "full",
  className,
  asLink = true,
}: LogoProps) {
  const { resolvedTheme } = useTheme()
  const accentClass =
    resolvedTheme === "dark" ? "text-primary-foreground" : "text-primary"

  const content =
    variant === "responsive" ? (
      <>
        <span
          className={cn(
            "text-lg font-semibold tracking-tight group-data-[collapsible=icon]:hidden",
            accentClass,
            className,
          )}
        >
          Wallet
        </span>
        <span
          className={cn(
            "hidden text-base font-semibold group-data-[collapsible=icon]:block",
            accentClass,
            className,
          )}
        >
          W
        </span>
      </>
    ) : (
      <span
        className={cn(
          variant === "full" ? "text-xl font-semibold" : "text-base font-semibold",
          accentClass,
          className,
        )}
      >
        {variant === "icon" ? "W" : "Wallet"}
      </span>
    )

  if (!asLink) {
    return content
  }

  return <Link to="/">{content}</Link>
}
