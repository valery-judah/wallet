import {
  ConversationsService,
  TurnsService,
  type ControlAction,
  type ConversationResponse,
  type SubmitTurnRequest,
  type SubmitTurnResponse,
  type TaskActionOfferResponse,
} from "@/client"

export type TurnInput = SubmitTurnRequest["input"]

export type PendingTurn = {
  request: SubmitTurnRequest
  label: string
}

export function createPendingTurn(
  input: TurnInput,
  label: string,
  conversationId: string | null,
): PendingTurn {
  return {
    request: {
      request_id: crypto.randomUUID(),
      ...(conversationId === null ? {} : { conversation_id: conversationId }),
      input,
    },
    label,
  }
}

export function messageInput(content: string): TurnInput {
  return { kind: "message", content }
}

export function helpInput(): TurnInput {
  return { kind: "control_action", action: "help" }
}

export function guardedControlInput(
  action: Exclude<ControlAction, "help">,
  conversation: ConversationResponse,
): TurnInput {
  const task = conversation.active_task
  if (task === null) {
    throw new Error(`${action} requires an active task`)
  }
  return {
    kind: "control_action",
    action,
    expected_task_id: task.id,
    expected_conversation_version: conversation.version,
  }
}

export function taskActionInput(offer: TaskActionOfferResponse): TurnInput {
  return {
    kind: "task_action",
    expected_task_id: offer.expected_task_id,
    expected_conversation_version: offer.expected_conversation_version,
    action: offer.action,
    payload: offer.payload ?? {},
  }
}

export async function submitTurn(turn: PendingTurn): Promise<SubmitTurnResponse> {
  return TurnsService.turnsSubmitConversationTurn<true>({
    body: turn.request,
    throwOnError: true,
  }).then((response) => response.data)
}

export async function readConversation(
  conversationId: string,
): Promise<ConversationResponse> {
  return ConversationsService.conversationsGetConversation<true>({
    path: { conversation_id: conversationId },
    throwOnError: true,
  }).then((response) => response.data)
}

export function errorDetail(error: unknown): string | null {
  if (typeof error !== "object" || error === null || !("detail" in error)) {
    return null
  }
  const detail = error.detail
  return typeof detail === "string" && detail.trim().length > 0 ? detail : null
}

export function isMissingConversationError(error: unknown): boolean {
  return errorDetail(error)?.startsWith("conversation not found:") ?? false
}

export function isStaleTurnError(error: unknown): boolean {
  return errorDetail(error) === "turn target or conversation version is stale"
}
