import { Link } from "@tanstack/react-router"
import type { CardResponse } from "@/client"
import { formatDate, formatMoney } from "@/lib/format"

type CardListProps = {
  cards: Array<CardResponse>
}

export function CardList({ cards }: CardListProps) {
  if (cards.length === 0) {
    return (
      <section className="surface rounded-[2rem] p-8 text-center">
        <p className="text-lg font-semibold">No cards yet.</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Create your first card to start tracking money movement.
        </p>
        <Link
          className="mt-6 inline-flex rounded-full bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90"
          to="/cards/new"
        >
          Create a card
        </Link>
      </section>
    )
  }

  return (
    <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
      {cards.map((card) => (
        <article className="surface rounded-[2rem] p-6" key={card.id}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                {card.currency}
              </p>
              <h2 className="mt-2 text-2xl font-semibold">{card.name}</h2>
            </div>
            <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
              Active
            </span>
          </div>

          <p className="mt-8 text-3xl font-semibold">
            {formatMoney(card.balance.amount_minor, card.balance.currency)}
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            Opened {formatDate(card.created_on)}
          </p>

          <Link
            className="mt-8 inline-flex rounded-full border border-border px-4 py-2 text-sm font-semibold text-foreground transition hover:bg-accent"
            params={{ cardId: card.id }}
            to="/cards/$cardId"
          >
            Open card
          </Link>
        </article>
      ))}
    </section>
  )
}
