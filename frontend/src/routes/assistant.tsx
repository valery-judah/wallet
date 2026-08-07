import { useQueryClient } from "@tanstack/react-query"
import {
  Check,
  CircleHelp,
  Copy,
  RefreshCcw,
  RotateCcw,
  Send,
  Square,
  Trash2,
} from "lucide-react"
import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react"
import type {
  ConversationResponse,
  SubmitTurnResponse,
  TaskActionOfferResponse,
  TaskViewResponse,
  TurnOutcomeResponse,
} from "@/client"
import { CapabilitySummary } from "@/components/assistant/capability-summary"
import { Button } from "@/components/ui/button"
import { accountKeys } from "@/lib/accounts"
import { getApiErrorMessage } from "@/lib/api-errors"
import {
  createPendingTurn,
  guardedControlInput,
  helpInput,
  isMissingConversationError,
  isStaleTurnError,
  messageInput,
  type PendingTurn,
  readConversation,
  submitTurn,
  taskActionInput,
  type TurnInput,
} from "@/lib/conversations"
import { transactionKeys } from "@/lib/transactions"

const SESSION_KEY = "wallet-assistant-session-v1"

type UserEntry = {
  id: string
  role: "user"
  label: string
}

type AssistantEntry = {
  id: string
  role: "assistant"
  outcome: TurnOutcomeResponse
  conversationVersion: number
  taskId: string | null
  taskVersion: number | null
}

type ErrorEntry = {
  id: string
  role: "error"
  message: string
  requestId: string | null
}

type NoticeEntry = {
  id: string
  role: "notice"
  message: string
}

type ChatEntry = UserEntry | AssistantEntry | ErrorEntry | NoticeEntry

type AssistantSession = {
  transcript: ChatEntry[]
  conversation: ConversationResponse | null
  pending: PendingTurn | null
}

const EMPTY_SESSION: AssistantSession = {
  transcript: [],
  conversation: null,
  pending: null,
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function isActionOffer(value: unknown): value is TaskActionOfferResponse {
  return (
    isRecord(value) &&
    typeof value.action === "string" &&
    typeof value.label === "string" &&
    typeof value.expected_task_id === "string" &&
    typeof value.expected_conversation_version === "number"
  )
}

function isTaskView(value: unknown): value is TaskViewResponse {
  return (
    isRecord(value) &&
    typeof value.kind === "string" &&
    isRecord(value.data) &&
    Array.isArray(value.available_actions) &&
    value.available_actions.every(isActionOffer)
  )
}

function isOutcome(value: unknown): value is TurnOutcomeResponse {
  return (
    isRecord(value) &&
    typeof value.kind === "string" &&
    typeof value.message === "string" &&
    (value.view === undefined || value.view === null || isTaskView(value.view))
  )
}

function isConversation(value: unknown): value is ConversationResponse {
  if (
    !isRecord(value) ||
    typeof value.id !== "string" ||
    typeof value.version !== "number" ||
    !(value.last_outcome === null || isOutcome(value.last_outcome))
  ) {
    return false
  }
  const task = value.active_task
  return (
    task === null ||
    (isRecord(task) &&
      typeof task.id === "string" &&
      typeof task.version === "number" &&
      isTaskView(task.view))
  )
}

function isTurnInput(value: unknown): value is TurnInput {
  if (!isRecord(value)) {
    return false
  }
  if (value.kind === "message") {
    return typeof value.content === "string"
  }
  if (value.kind === "control_action") {
    return value.action === "help" || value.action === "cancel" || value.action === "restart"
  }
  return (
    value.kind === "task_action" &&
    typeof value.expected_task_id === "string" &&
    typeof value.expected_conversation_version === "number" &&
    typeof value.action === "string"
  )
}

function isPendingTurn(value: unknown): value is PendingTurn {
  return (
    isRecord(value) &&
    typeof value.label === "string" &&
    isRecord(value.request) &&
    typeof value.request.request_id === "string" &&
    isTurnInput(value.request.input)
  )
}

function isChatEntry(value: unknown): value is ChatEntry {
  if (!isRecord(value) || typeof value.id !== "string" || typeof value.role !== "string") {
    return false
  }
  if (value.role === "user") {
    return typeof value.label === "string"
  }
  if (value.role === "assistant") {
    return (
      isOutcome(value.outcome) &&
      typeof value.conversationVersion === "number" &&
      (value.taskId === null || typeof value.taskId === "string") &&
      (value.taskVersion === null || typeof value.taskVersion === "number")
    )
  }
  if (value.role === "error") {
    return (
      typeof value.message === "string" &&
      (value.requestId === null || typeof value.requestId === "string")
    )
  }
  return value.role === "notice" && typeof value.message === "string"
}

function loadSession(): AssistantSession {
  try {
    const stored = sessionStorage.getItem(SESSION_KEY)
    if (stored === null) {
      return EMPTY_SESSION
    }
    const parsed: unknown = JSON.parse(stored)
    if (
      !isRecord(parsed) ||
      parsed.version !== 1 ||
      !Array.isArray(parsed.transcript) ||
      !parsed.transcript.every(isChatEntry) ||
      !(parsed.conversation === null || isConversation(parsed.conversation)) ||
      !(parsed.pending === null || isPendingTurn(parsed.pending))
    ) {
      sessionStorage.removeItem(SESSION_KEY)
      return EMPTY_SESSION
    }
    return {
      transcript: parsed.transcript,
      conversation: parsed.conversation,
      pending: parsed.pending,
    }
  } catch {
    sessionStorage.removeItem(SESSION_KEY)
    return EMPTY_SESSION
  }
}

function persistSession(session: AssistantSession): void {
  if (
    session.transcript.length === 0 &&
    session.conversation === null &&
    session.pending === null
  ) {
    sessionStorage.removeItem(SESSION_KEY)
    return
  }
  sessionStorage.setItem(SESSION_KEY, JSON.stringify({ version: 1, ...session }))
}

function assistantEntry(response: SubmitTurnResponse): AssistantEntry {
  const task = response.conversation.active_task
  return {
    id: crypto.randomUUID(),
    role: "assistant",
    outcome: response.outcome,
    conversationVersion: response.conversation.version,
    taskId: task?.id ?? null,
    taskVersion: task?.version ?? null,
  }
}

function safeJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return "Unable to display structured data."
  }
}

function formatExchange(userMessage: string, entry: AssistantEntry): string {
  const view = entry.outcome.view
  const lines = [
    "User message:",
    userMessage,
    "",
    "Assistant answer:",
    entry.outcome.message,
    "",
    "Details:",
    `Outcome: ${entry.outcome.kind}`,
    `Conversation version: ${entry.conversationVersion}`,
    `Task ID: ${entry.taskId ?? "none"}`,
    `Task version: ${entry.taskVersion ?? "none"}`,
    `View: ${view?.kind ?? "none"}`,
  ]
  if (view) {
    lines.push("", "View data:", safeJson(view.data))
  }
  return lines.join("\n")
}

function userMessageBefore(entries: ChatEntry[], entryIndex: number): string {
  for (let index = entryIndex - 1; index >= 0; index -= 1) {
    const entry = entries[index]
    if (entry.role === "user") {
      return entry.label
    }
    if (entry.role === "assistant") {
      break
    }
  }
  return "Not available"
}

function CopyExchangeButton({ value }: { value: string }) {
  const [status, setStatus] = useState<"idle" | "copied" | "failed">("idle")

  useEffect(() => {
    if (status === "idle") {
      return
    }
    const timeout = window.setTimeout(() => setStatus("idle"), 2000)
    return () => window.clearTimeout(timeout)
  }, [status])

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setStatus("copied")
    } catch {
      setStatus("failed")
    }
  }

  const buttonLabel =
    status === "copied"
      ? "Message-answer pair copied"
      : status === "failed"
        ? "Retry copying message-answer pair"
        : "Copy message-answer pair with details"

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      className="h-7 px-2 text-xs text-muted-foreground"
      aria-label={buttonLabel}
      onClick={() => void handleCopy()}
    >
      {status === "copied" ? <Check /> : <Copy />}
      <span aria-live="polite">
        {status === "copied" ? "Copied" : status === "failed" ? "Try again" : "Copy pair"}
      </span>
    </Button>
  )
}

function AssistantMessage({ entry, userMessage }: { entry: AssistantEntry; userMessage: string }) {
  const view = entry.outcome.view
  return (
    <div className="max-w-3xl">
      <article className="rounded-2xl rounded-bl-md border bg-card p-4 shadow-sm">
        <p className="whitespace-pre-wrap text-sm leading-6">{entry.outcome.message}</p>
        {view && <CapabilitySummary view={view} />}
        <details className="mt-3 border-t pt-3 text-xs text-muted-foreground">
          <summary className="cursor-pointer select-none font-medium text-foreground">Details</summary>
          <dl className="mt-3 grid gap-1 sm:grid-cols-2">
            <div>Outcome: {entry.outcome.kind}</div>
            <div>Conversation version: {entry.conversationVersion}</div>
            <div>Task ID: {entry.taskId ?? "none"}</div>
            <div>Task version: {entry.taskVersion ?? "none"}</div>
            <div>View: {view?.kind ?? "none"}</div>
          </dl>
          {view && (
            <pre className="mt-3 max-h-72 overflow-auto rounded-lg bg-muted p-3 text-[0.7rem] leading-5 text-foreground">
              {safeJson(view.data)}
            </pre>
          )}
        </details>
      </article>
      <CopyExchangeButton value={formatExchange(userMessage, entry)} />
    </div>
  )
}

export function AssistantRoute() {
  const [initialSession] = useState(loadSession)
  const [transcript, setTranscript] = useState(initialSession.transcript)
  const [conversation, setConversation] = useState(initialSession.conversation)
  const [pending, setPending] = useState(initialSession.pending)
  const [draft, setDraft] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isRestoring, setIsRestoring] = useState(initialSession.conversation !== null)
  const [restoreError, setRestoreError] = useState<string | null>(null)
  const restoreStarted = useRef(false)
  const composerRef = useRef<HTMLTextAreaElement>(null)
  const transcriptEndRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()

  useEffect(() => {
    persistSession({ transcript, conversation, pending })
  }, [conversation, pending, transcript])

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" })
  }, [isSubmitting, transcript])

  const validateRestoredConversation = async (current: ConversationResponse) => {
    setIsRestoring(true)
    setRestoreError(null)
    try {
      setConversation(await readConversation(current.id))
    } catch (error) {
      if (isMissingConversationError(error)) {
        setConversation(null)
        setPending(null)
        setTranscript([
          {
            id: crypto.randomUUID(),
            role: "notice",
            message: "The previous chat expired after the server restarted. Start a new message.",
          },
        ])
      } else {
        setRestoreError(
          getApiErrorMessage(error, "Unable to reconnect to the previous conversation."),
        )
      }
    } finally {
      setIsRestoring(false)
    }
  }

  useEffect(() => {
    if (initialSession.conversation === null || restoreStarted.current) {
      return
    }
    restoreStarted.current = true
    void validateRestoredConversation(initialSession.conversation)
  }, [initialSession.conversation])

  const focusComposer = () => {
    window.setTimeout(() => composerRef.current?.focus(), 0)
  }

  const refreshConversationAfterConflict = async (conversationId: string) => {
    try {
      setConversation(await readConversation(conversationId))
    } catch {
      // The conflict is already visible in the transcript. A later retry or refresh can reconnect.
    }
  }

  const executeTurn = async (turn: PendingTurn, appendUser: boolean) => {
    if (appendUser) {
      setTranscript((entries) => [
        ...entries,
        { id: crypto.randomUUID(), role: "user", label: turn.label },
      ])
    } else {
      setTranscript((entries) =>
        entries.filter(
          (entry) => entry.role !== "error" || entry.requestId !== turn.request.request_id,
        ),
      )
    }
    setPending(turn)
    setIsSubmitting(true)
    try {
      const response = await submitTurn(turn)
      setConversation(response.conversation)
      setTranscript((entries) => [...entries, assistantEntry(response)])
      setPending(null)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: accountKeys.all }),
        queryClient.invalidateQueries({ queryKey: transactionKeys.all }),
      ])
    } catch (error) {
      if (isMissingConversationError(error)) {
        setConversation(null)
        setPending(null)
        setTranscript([
          {
            id: crypto.randomUUID(),
            role: "notice",
            message: "This chat expired after the server restarted. Please send your message again.",
          },
        ])
      } else if (isStaleTurnError(error)) {
        setPending(null)
        setTranscript((entries) => [
          ...entries,
          {
            id: crypto.randomUUID(),
            role: "error",
            message: "This action is no longer current. Continue from the latest assistant response.",
            requestId: null,
          },
        ])
        const conversationId = turn.request.conversation_id
        if (conversationId) {
          await refreshConversationAfterConflict(conversationId)
        }
      } else {
        setTranscript((entries) => [
          ...entries,
          {
            id: crypto.randomUUID(),
            role: "error",
            message: getApiErrorMessage(error, "Unable to send this turn."),
            requestId: turn.request.request_id,
          },
        ])
      }
    } finally {
      setIsSubmitting(false)
      focusComposer()
    }
  }

  const submitInput = (input: TurnInput, label: string) => {
    if (isSubmitting || pending !== null || isRestoring || restoreError !== null) {
      return
    }
    const turn = createPendingTurn(input, label, conversation?.id ?? null)
    void executeTurn(turn, true)
  }

  const handleMessageSubmit = (event?: FormEvent) => {
    event?.preventDefault()
    const content = draft.trim()
    if (content.length === 0) {
      return
    }
    setDraft("")
    submitInput(messageInput(content), content)
  }

  const handleComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      handleMessageSubmit()
    }
  }

  const handleControl = (action: "help" | "cancel" | "restart") => {
    if (action === "help") {
      submitInput(helpInput(), "Help")
      return
    }
    if (conversation?.active_task === null || conversation === null) {
      return
    }
    submitInput(guardedControlInput(action, conversation), action === "cancel" ? "Cancel" : "Restart")
  }

  const handleTaskAction = (offer: TaskActionOfferResponse) => {
    submitInput(taskActionInput(offer), offer.label)
  }

  const handleNewChat = () => {
    sessionStorage.removeItem(SESSION_KEY)
    setTranscript([])
    setConversation(null)
    setPending(null)
    setDraft("")
    setRestoreError(null)
    setIsRestoring(false)
    focusComposer()
  }

  const isBlocked = isSubmitting || pending !== null || isRestoring || restoreError !== null
  const activeTask = conversation?.active_task ?? null
  const availableActions = activeTask?.view.available_actions ?? []

  return (
    <section className="mx-auto flex min-h-[calc(100vh-12rem)] max-w-4xl flex-col gap-4">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black tracking-[-0.04em]">Wallet Assistant</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {activeTask ? `Active task · conversation v${conversation?.version}` : "Ready for a new task"}
          </p>
        </div>
        <Button type="button" variant="outline" onClick={handleNewChat} disabled={isSubmitting}>
          <Trash2 />
          New chat
        </Button>
      </header>

      <div className="flex min-h-[30rem] flex-1 flex-col overflow-hidden rounded-[2rem] border bg-muted/30 shadow-sm">
        <div
          className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6"
          aria-live="polite"
          aria-label="Conversation"
        >
          {transcript.length === 0 && (
            <div className="mx-auto max-w-lg py-16 text-center">
              <p className="text-xl font-semibold">What would you like to do?</p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                Ask for your balances or describe an expense, income, transfer, or balance adjustment.
              </p>
              <div className="mt-5 flex flex-wrap justify-center gap-2">
                {["Show my current balances", "Record an expense"].map((suggestion) => (
                  <Button
                    key={suggestion}
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={isBlocked}
                    onClick={() => submitInput(messageInput(suggestion), suggestion)}
                  >
                    {suggestion}
                  </Button>
                ))}
              </div>
            </div>
          )}

          {transcript.map((entry, entryIndex) => {
            if (entry.role === "user") {
              return (
                <div key={entry.id} className="flex justify-end">
                  <article className="max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-3 text-sm leading-6 text-primary-foreground">
                    {entry.label}
                  </article>
                </div>
              )
            }
            if (entry.role === "assistant") {
              return (
                <AssistantMessage
                  key={entry.id}
                  entry={entry}
                  userMessage={userMessageBefore(transcript, entryIndex)}
                />
              )
            }
            if (entry.role === "notice") {
              return (
                <p key={entry.id} className="mx-auto max-w-xl rounded-xl bg-muted px-4 py-3 text-center text-sm text-muted-foreground">
                  {entry.message}
                </p>
              )
            }
            const canRetry = pending?.request.request_id === entry.requestId
            return (
              <article key={entry.id} className="max-w-3xl rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm">
                <p className="text-destructive">{entry.message}</p>
                {canRetry && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="mt-3"
                    disabled={isSubmitting}
                    onClick={() => void executeTurn(pending, false)}
                  >
                    <RefreshCcw />
                    Retry safely
                  </Button>
                )}
              </article>
            )
          })}

          {pending !== null && !isSubmitting && !transcript.some(
            (entry) => entry.role === "error" && entry.requestId === pending.request.request_id,
          ) && (
            <article className="max-w-3xl rounded-xl border bg-card p-4 text-sm">
              <p>This turn may have completed before the page refreshed.</p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={() => void executeTurn(pending, false)}
              >
                <RefreshCcw />
                Retry safely
              </Button>
            </article>
          )}

          {isSubmitting && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
              <span className="size-2 animate-pulse rounded-full bg-primary" />
              Wallet Assistant is working…
            </div>
          )}

          {availableActions.length > 0 && (
            <div className="flex flex-wrap gap-2" aria-label="Available task actions">
              {availableActions.map((offer) => (
                <Button
                  key={`${offer.action}-${offer.expected_conversation_version}`}
                  type="button"
                  disabled={isBlocked}
                  onClick={() => handleTaskAction(offer)}
                >
                  {offer.label}
                </Button>
              ))}
            </div>
          )}
          <div ref={transcriptEndRef} />
        </div>

        <div className="border-t bg-card p-4 sm:p-5">
          {restoreError && conversation && (
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-destructive/40 bg-destructive/5 p-3 text-sm">
              <span>{restoreError}</span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => void validateRestoredConversation(conversation)}
              >
                <RefreshCcw />
                Reconnect
              </Button>
            </div>
          )}
          <form className="flex items-end gap-3" onSubmit={handleMessageSubmit}>
            <label className="sr-only" htmlFor="assistant-message">
              Message the wallet
            </label>
            <textarea
              ref={composerRef}
              id="assistant-message"
              rows={2}
              maxLength={4000}
              value={draft}
              disabled={isBlocked}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              placeholder="Message the wallet…"
              className="min-h-12 flex-1 resize-none rounded-xl border bg-background px-4 py-3 text-sm shadow-xs outline-none transition focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
            />
            <Button
              type="submit"
              size="icon-lg"
              aria-label="Send message"
              disabled={isBlocked || draft.trim().length === 0}
            >
              <Send />
            </Button>
          </form>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={isBlocked}
              onClick={() => handleControl("help")}
            >
              <CircleHelp />
              Help
            </Button>
            {activeTask && (
              <>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={isBlocked}
                  onClick={() => handleControl("cancel")}
                >
                  <Square />
                  Cancel
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={isBlocked}
                  onClick={() => handleControl("restart")}
                >
                  <RotateCcw />
                  Restart
                </Button>
              </>
            )}
            {conversation && (
              <span className="ml-auto text-xs text-muted-foreground">
                Conversation v{conversation.version}
              </span>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
