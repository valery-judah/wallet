import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link, useParams } from "@tanstack/react-router"
import { useState } from "react"
import type { CardResponse } from "@/client"
import { WithdrawForm } from "@/components/cards/withdraw-form"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  cardDetailOptions,
  cardKeys,
  upsertCardInList,
  withdrawFromCard,
} from "@/lib/cards"
import { getApiErrorMessage } from "@/lib/api-errors"
import { formatDate, formatMoney } from "@/lib/format"

export function CardDetailRoute() {
  const { cardId } = useParams({ from: "/cards/$cardId" })
  const queryClient = useQueryClient()
  const [errorMessage, setErrorMessage] = useState<string>()
  const cardQuery = useQuery(cardDetailOptions(cardId))

  const withdrawMutation = useMutation({
    mutationFn: (values: { amount_minor: number; currency: string }) =>
      withdrawFromCard(cardId, values),
    onSuccess: async (card) => {
      setErrorMessage(undefined)
      queryClient.setQueryData(cardKeys.detail(cardId), card)
      queryClient.setQueryData<Array<CardResponse>>(
        cardKeys.list(),
        (cards) => upsertCardInList(cards, card),
      )
      await queryClient.invalidateQueries({ queryKey: cardKeys.list() })
    },
  })

  async function handleWithdraw(values: {
    amount_minor: number
    currency: string
  }) {
    setErrorMessage(undefined)

    try {
      await withdrawMutation.mutateAsync(values)
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error))
    }
  }

  if (cardQuery.isLoading) {
    return (
      <section className="rounded-xl border bg-card p-8 shadow-sm">
        <p className="text-lg font-semibold">Loading card...</p>
      </section>
    )
  }

  if (cardQuery.isError) {
    return (
      <section className="rounded-xl border bg-card p-8 shadow-sm">
        <p className="text-lg font-semibold">Unable to load this card.</p>
        <p className="mt-2 text-sm text-destructive">
          {getApiErrorMessage(cardQuery.error)}
        </p>
        <Link
          className="mt-6 inline-flex rounded-md border bg-background px-4 py-2 text-sm font-semibold transition hover:bg-accent"
          to="/cards"
        >
          Back to cards
        </Link>
      </section>
    )
  }

  const card = cardQuery.data

  if (!card) {
    return (
      <section className="rounded-xl border bg-card p-8 shadow-sm">
        <p className="text-lg font-semibold">Card data is unavailable.</p>
      </section>
    )
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
      <Card>
        <CardHeader>
          <CardTitle>{card.name}</CardTitle>
          <CardDescription>
            Card ID: {card.id} · Opened {formatDate(card.created_on)}
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border bg-muted/40 p-4">
              <p className="text-sm text-muted-foreground">Current balance</p>
              <p className="mt-2 text-3xl font-semibold">
                {formatMoney(card.balance.amount_minor, card.balance.currency)}
              </p>
            </div>
            <div className="rounded-lg border bg-muted/20 p-4">
              <dl className="grid gap-3 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-muted-foreground">Currency</dt>
                  <dd className="font-medium">{card.currency}</dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-muted-foreground">Created on</dt>
                  <dd className="font-medium">{formatDate(card.created_on)}</dd>
                </div>
              </dl>
            </div>
          </div>

          <div>
            <Link
              className="text-sm font-medium text-primary hover:underline"
              to="/cards"
            >
              Back to cards
            </Link>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Withdraw money</CardTitle>
          <CardDescription>
            Enter an amount in minor units to withdraw from this card.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <WithdrawForm
            currency={card.currency}
            errorMessage={errorMessage}
            isPending={withdrawMutation.isPending}
            onSubmit={handleWithdraw}
          />
        </CardContent>
      </Card>
    </div>
  )
}
