import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import type { CardResponse } from "@/client"
import { CreateCardForm } from "@/components/cards/create-card-form"
import { createCard, cardKeys, upsertCardInList } from "@/lib/cards"
import { getApiErrorMessage } from "@/lib/api-errors"

export function CardsNewRoute() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [errorMessage, setErrorMessage] = useState<string>()

  const createCardMutation = useMutation({
    mutationFn: createCard,
    onSuccess: async (card) => {
      queryClient.setQueryData(cardKeys.detail(card.id), card)
      queryClient.setQueryData<Array<CardResponse>>(
        cardKeys.list(),
        (cards) => upsertCardInList(cards, card),
      )
      await queryClient.invalidateQueries({ queryKey: cardKeys.list() })
      await navigate({
        to: "/cards/$cardId",
        params: { cardId: card.id },
      })
    },
  })

  async function handleSubmit(values: {
    name: string
    currency: string
    opened_on?: string
  }) {
    setErrorMessage(undefined)

    try {
      await createCardMutation.mutateAsync(values)
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error))
    }
  }

  return (
    <div className="grid gap-6">
      <section className="max-w-3xl">
        <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">
          New card
        </p>
        <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">
          Add a fresh card before money starts moving.
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Choose a name, set the card currency, and optionally record the
          opening date.
        </p>
      </section>

      <CreateCardForm
        errorMessage={errorMessage}
        isPending={createCardMutation.isPending}
        onSubmit={handleSubmit}
      />
    </div>
  )
}
