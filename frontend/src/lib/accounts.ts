import { queryOptions } from "@tanstack/react-query"
import {
  AccountsService,
  type AccountResponse,
  type CreateAccountRequest,
  type UpdateAccountProfileRequest,
} from "@/client"

const STALE_TIME_MS = 30_000

export const accountKeys = {
  all: ["accounts"] as const,
  list: () => [...accountKeys.all, "list"] as const,
  detail: (accountId: string) =>
    [...accountKeys.all, "detail", accountId] as const,
}

export function accountsListOptions() {
  return queryOptions({
    queryKey: accountKeys.list(),
    queryFn: () =>
      AccountsService.accountsListAccounts<true>({
        throwOnError: true,
      }).then((result) => result.data),
    staleTime: STALE_TIME_MS,
  })
}

export function accountDetailOptions(accountId: string) {
  return queryOptions({
    queryKey: accountKeys.detail(accountId),
    queryFn: () =>
      AccountsService.accountsGetAccount<true>({
        path: { account_id: accountId },
        throwOnError: true,
      }).then((result) => result.data),
    staleTime: STALE_TIME_MS,
  })
}

export function createAccount(
  payload: CreateAccountRequest,
): Promise<AccountResponse> {
  return AccountsService.accountsCreateAccount<true>({
    body: payload,
    throwOnError: true,
  }).then((result) => result.data)
}

export function updateAccountProfile(
  accountId: string,
  payload: UpdateAccountProfileRequest,
): Promise<AccountResponse> {
  return AccountsService.accountsUpdateAccountProfile<true>({
    path: { account_id: accountId },
    body: payload,
    throwOnError: true,
  }).then((result) => result.data)
}

export function archiveAccount(accountId: string): Promise<AccountResponse> {
  return AccountsService.accountsArchiveAccount<true>({
    path: { account_id: accountId },
    throwOnError: true,
  }).then((result) => result.data)
}

export function upsertAccountInList(
  accounts: Array<AccountResponse> | undefined,
  account: AccountResponse,
): Array<AccountResponse> {
  if (!accounts) {
    return [account]
  }

  const existingIndex = accounts.findIndex((item) => item.id === account.id)

  if (existingIndex === -1) {
    return [account, ...accounts]
  }

  return accounts.map((item) => (item.id === account.id ? account : item))
}
