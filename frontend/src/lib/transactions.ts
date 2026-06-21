import { queryOptions } from "@tanstack/react-query"
import {
  TransactionsService,
  type CreateTransactionRequest,
  type TransactionResponse,
} from "@/client"

const STALE_TIME_MS = 30_000

export const transactionKeys = {
  all: ["transactions"] as const,
  list: (accountId?: string) =>
    [...transactionKeys.all, "list", accountId ?? "all"] as const,
  detail: (transactionId: string) =>
    [...transactionKeys.all, "detail", transactionId] as const,
}

export function transactionsListOptions(accountId?: string) {
  return queryOptions({
    queryKey: transactionKeys.list(accountId),
    queryFn: () =>
      TransactionsService.transactionsListTransactions<true>({
        query: accountId ? { account_id: accountId } : undefined,
        throwOnError: true,
      }).then((result) => result.data),
    staleTime: STALE_TIME_MS,
  })
}

export function createTransaction(
  payload: CreateTransactionRequest,
): Promise<TransactionResponse> {
  return TransactionsService.transactionsCreateTransaction<true>({
    body: payload,
    throwOnError: true,
  }).then((result) => result.data)
}
