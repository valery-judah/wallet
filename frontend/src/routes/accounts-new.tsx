import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import type { AccountResponse } from "@/client"
import type { AccountTypeValue } from "@/components/accounts/account-appearance"
import { AccountPageIntro, AccountSectionStack } from "@/components/accounts/account-layout"
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
    type: AccountTypeValue
    currency: string
    opening_balance_minor: number
    opened_on?: string
    color_key?: string
  }) {
    setErrorMessage(undefined)

    try {
      await createAccountMutation.mutateAsync(values)
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error))
    }
  }

  return (
    <AccountSectionStack>
      <AccountPageIntro
        description="Choose the account type, currency, and opening balance for this account."
        eyebrow="New account"
        title="Set up a new account."
      />
      <CreateAccountForm
        errorMessage={errorMessage}
        isPending={createAccountMutation.isPending}
        onSubmit={handleSubmit}
      />
    </AccountSectionStack>
  )
}
