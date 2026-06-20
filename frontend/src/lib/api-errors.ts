type ValidationErrorItem = {
  msg?: string
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null
}

export function getApiErrorMessage(
  error: unknown,
  fallback = "Something went wrong.",
): string {
  if (isRecord(error)) {
    const detail = error.detail

    if (typeof detail === "string" && detail.trim().length > 0) {
      return detail
    }

    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => (isRecord(item) ? (item as ValidationErrorItem).msg : ""))
        .filter((item): item is string => Boolean(item))

      if (messages.length > 0) {
        return messages.join(", ")
      }
    }
  }

  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message
  }

  return fallback
}
