import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import type { AccountResponse } from "@/client"
import { CreateAccountForm } from "@/components/accounts/create-account-form"
import { getApiErrorMessage } from "@/lib/api-errors"
import { accountKeys, createAccount, upsertAccountInList } from "@/lib/accounts"

export function AccountsNewRoute() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [errorMessage, setErrorMessage] = useState<string>()

  const createAccountMutation = useMutation({
    mutationFn: createAccount,
    onSuccess: async (account) => {
      queryClient.setQueryData(accountKeys.detail(account.id), account)
      queryClient.setQueryData<Array<AccountResponse>>(
        accountKeys.list(),
        (accounts) => upsertAccountInList(accounts, account),
      )
      await queryClient.invalidateQueries({ queryKey: accountKeys.list() })
      await navigate({
        to: "/accounts/$accountId",
        params: { accountId: account.id },
      })
    },
  })

  async function handleSubmit(values: {
    name: string
    type: "card" | "cash" | "bank" | "wallet" | "platform" | "savings" | "other"
    currency: string
    current_balance_minor: number
    opened_on?: string
    color_key?: string
    icon_key?: string
  }) {
    setErrorMessage(undefined)

    try {
      await createAccountMutation.mutateAsync(values)
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error))
    }
  }

  return (
    <div className="grid gap-6">
      <section className="max-w-3xl">
        <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">
          New account
        </p>
        <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">
          Add a new account before money starts moving.
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Choose the account type, set the currency, and record the current
          balance you want to start from.
        </p>
      </section>

      <CreateAccountForm
        errorMessage={errorMessage}
        isPending={createAccountMutation.isPending}
        onSubmit={handleSubmit}
      />
    </div>
  )
}
