import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { CardList } from "@/components/cards/card-list"
import { Button } from "@/components/ui/button"
import { cardsListOptions } from "@/lib/cards"
import { getApiErrorMessage } from "@/lib/api-errors"

export function CardsListRoute() {
  const cardsQuery = useQuery(cardsListOptions())

  if (cardsQuery.isLoading) {
    return (
      <section className="surface rounded-[2rem] p-8">
        <p className="text-lg font-semibold">Loading cards...</p>
      </section>
    )
  }

  if (cardsQuery.isError) {
    return (
      <section className="surface rounded-[2rem] p-8">
        <p className="text-lg font-semibold">Unable to load cards.</p>
        <p className="mt-2 text-sm text-destructive">
          {getApiErrorMessage(cardsQuery.error)}
        </p>
      </section>
    )
  }

  const cards = cardsQuery.data ?? []

  return (
    <div className="grid gap-8">
      <section className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">
            Cards
          </p>
          <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">
            See every card and its current balance.
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Open an existing card or create a new one before money starts
            moving.
          </p>
        </div>
        <Button asChild>
          <Link to="/cards/new">New card</Link>
        </Button>
      </section>

      <CardList cards={cards} />
    </div>
  )
}
