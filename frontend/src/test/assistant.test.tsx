import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import {
  ConversationsService,
  TurnsService,
  type ConversationResponse,
  type SubmitTurnResponse,
  type TaskActionOfferResponse,
  type TaskViewResponse,
  type TurnOutcomeResponse,
} from "@/client"
import { renderApp } from "@/test/render-app"

const SESSION_KEY = "wallet-assistant-session-v1"

function buildSuccess<T>(data: T) {
  return {
    data,
    request: new Request("http://localhost:8000"),
    response: new Response(),
  }
}

function captureView(
  overrides: Partial<TaskViewResponse> = {},
): TaskViewResponse {
  return {
    kind: "transaction_capture",
    data: {
      phase: "awaiting_confirmation",
      candidate: {
        type: "expense",
        amount_minor: 4000,
        occurred_on: "2026-08-06",
        account_id: "cash-usd",
        spending_category_id: "groceries",
        income_category_id: null,
        source_account_id: null,
        destination_account_id: null,
        balance_change_minor: null,
        description: null,
        merchant_name: null,
        notes: null,
      },
      interaction: null,
    },
    available_actions: [confirmOffer()],
    ...overrides,
  }
}

function confirmOffer(
  overrides: Partial<TaskActionOfferResponse> = {},
): TaskActionOfferResponse {
  return {
    action: "confirm",
    label: "Confirm",
    payload: {},
    expected_task_id: "task-1",
    expected_conversation_version: 1,
    ...overrides,
  }
}

function buildConversation({
  version = 1,
  taskView = captureView(),
  active = true,
  outcome = null,
}: {
  version?: number
  taskView?: TaskViewResponse
  active?: boolean
  outcome?: TurnOutcomeResponse | null
} = {}): ConversationResponse {
  return {
    id: "conversation-1",
    version,
    active_task: active ? { id: "task-1", version, view: taskView } : null,
    last_outcome: outcome,
  }
}

function buildTurnResponse({
  version = 1,
  outcome,
  taskView,
  active = true,
}: {
  version?: number
  outcome?: TurnOutcomeResponse
  taskView?: TaskViewResponse
  active?: boolean
} = {}): SubmitTurnResponse {
  const resolvedView = taskView ?? captureView()
  const resolvedOutcome =
    outcome ??
    ({
      kind: "preview",
      message: "Ready to record: USD 40.00 expense from Cash for Groceries.",
      view: resolvedView,
      result: null,
    } satisfies TurnOutcomeResponse)
  return {
    request_id: `response-${version}`,
    conversation: buildConversation({
      version,
      taskView: resolvedView,
      active,
      outcome: resolvedOutcome,
    }),
    outcome: resolvedOutcome,
  }
}

function mockTurnResponses(...responses: SubmitTurnResponse[]) {
  const mock = vi.spyOn(TurnsService, "turnsSubmitConversationTurn")
  responses.forEach((response) => mock.mockResolvedValueOnce(buildSuccess(response)))
  return mock
}

describe("Wallet Assistant", () => {
  afterEach(() => {
    vi.restoreAllMocks()
    sessionStorage.clear()
  })

  it("creates a conversation, continues it, and renders capture details", async () => {
    const first = buildTurnResponse()
    const secondView = captureView({
      data: {
        phase: "active",
        candidate: {
          type: "expense",
          amount_minor: 4000,
          occurred_on: "2026-08-06",
        },
        interaction: {
          kind: "disambiguate",
          field: "spending_category_id",
          options: [
            { value: "coffee", label: "Food > Coffee" },
            { value: "work-coffee", label: "Work > Coffee" },
          ],
        },
      },
      available_actions: [],
    })
    const second = buildTurnResponse({
      version: 2,
      taskView: secondView,
      outcome: {
        kind: "selection_required",
        message: "Which spending category did you mean?",
        view: secondView,
        result: null,
      },
    })
    const submit = mockTurnResponses(first, second)
    const user = userEvent.setup()
    renderApp("/assistant")

    const composer = await screen.findByLabelText("Message the wallet")
    await user.type(composer, "Spent 40 USD on groceries{enter}")

    expect(await screen.findByText(/Ready to record:/)).toBeInTheDocument()
    expect(screen.getByLabelText("Transaction draft")).toBeInTheDocument()
    expect(submit.mock.calls[0][0].body).toMatchObject({
      input: { kind: "message", content: "Spent 40 USD on groceries" },
    })
    expect(submit.mock.calls[0][0].body).not.toHaveProperty("conversation_id")
    await waitFor(() => expect(composer).toHaveFocus())

    await user.type(composer, "Coffee{enter}")
    expect(await screen.findByText("Which spending category did you mean?")).toBeInTheDocument()
    expect(screen.getByText("Food > Coffee")).toBeInTheDocument()
    expect(screen.getByText("Work > Coffee")).toBeInTheDocument()
    expect(submit.mock.calls[1][0].body).toMatchObject({
      conversation_id: "conversation-1",
      input: { kind: "message", content: "Coffee" },
    })
  })

  it("copies the message-answer pair with complete details", async () => {
    const answer = "Ready to record: USD 40.00 expense from Cash for Groceries."
    const response = buildTurnResponse()
    mockTurnResponses(response)
    const user = userEvent.setup()
    const writeText = vi.spyOn(navigator.clipboard, "writeText")
    renderApp("/assistant")

    await user.type(await screen.findByLabelText("Message the wallet"), "Spent 40 USD{enter}")
    await screen.findByText(answer)

    await user.click(
      screen.getByRole("button", { name: "Copy message-answer pair with details" }),
    )
    expect(writeText).toHaveBeenLastCalledWith(
      [
        "User message:",
        "Spent 40 USD",
        "",
        "Assistant answer:",
        answer,
        "",
        "Details:",
        "Outcome: preview",
        "Conversation version: 1",
        "Task ID: task-1",
        "Task version: 1",
        "View: transaction_capture",
        "",
        "View data:",
        JSON.stringify(response.outcome.view?.data, null, 2),
      ].join("\n"),
    )
    expect(
      screen.getByRole("button", { name: "Message-answer pair copied" }),
    ).toBeInTheDocument()
  })

  it("sends exact capability and lifecycle action guards", async () => {
    const active = buildTurnResponse()
    const helped = buildTurnResponse({
      version: 2,
      taskView: captureView({
        available_actions: [confirmOffer({ expected_conversation_version: 2 })],
      }),
      outcome: { kind: "help", message: "I can help with transactions.", view: null },
    })
    const confirmed = buildTurnResponse({
      version: 3,
      active: false,
      outcome: { kind: "recorded", message: "Recorded.", view: null },
    })
    const submit = mockTurnResponses(active, helped, confirmed)
    const user = userEvent.setup()
    renderApp("/assistant")

    await user.type(await screen.findByLabelText("Message the wallet"), "Record an expense{enter}")
    await screen.findByText(/Ready to record:/)
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Restart" })).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Help" }))
    await screen.findByText("I can help with transactions.")
    expect(submit.mock.calls[1][0].body).toMatchObject({
      conversation_id: "conversation-1",
      input: { kind: "control_action", action: "help" },
    })
    expect(submit.mock.calls[1][0].body.input).not.toHaveProperty("expected_task_id")

    await user.click(screen.getByRole("button", { name: "Confirm" }))
    await screen.findByText("Recorded.")
    expect(submit.mock.calls[2][0].body).toMatchObject({
      conversation_id: "conversation-1",
      input: {
        kind: "task_action",
        action: "confirm",
        payload: {},
        expected_task_id: "task-1",
        expected_conversation_version: 2,
      },
    })
    expect(screen.queryByRole("button", { name: "Confirm" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument()
  })

  it("builds restart and cancel controls from the latest conversation", async () => {
    const restartedView = captureView({
      available_actions: [],
      data: { phase: "active", candidate: {}, interaction: null },
    })
    const restarted = buildTurnResponse({
      version: 2,
      taskView: restartedView,
      outcome: { kind: "restarted", message: "Current task restarted.", view: restartedView },
    })
    restarted.conversation.active_task = { id: "task-2", version: 1, view: restartedView }
    const cancelled = buildTurnResponse({
      version: 3,
      active: false,
      outcome: { kind: "current_task_cancelled", message: "Current task cancelled.", view: null },
    })
    const submit = mockTurnResponses(buildTurnResponse(), restarted, cancelled)
    const user = userEvent.setup()
    renderApp("/assistant")

    await user.type(await screen.findByLabelText("Message the wallet"), "Record an expense{enter}")
    await screen.findByText(/Ready to record:/)
    await user.click(screen.getByRole("button", { name: "Restart" }))
    await screen.findByText("Current task restarted.")
    expect(submit.mock.calls[1][0].body.input).toEqual({
      kind: "control_action",
      action: "restart",
      expected_task_id: "task-1",
      expected_conversation_version: 1,
    })

    await user.click(screen.getByRole("button", { name: "Cancel" }))
    await screen.findByText("Current task cancelled.")
    expect(submit.mock.calls[2][0].body.input).toEqual({
      kind: "control_action",
      action: "cancel",
      expected_task_id: "task-2",
      expected_conversation_version: 2,
    })
  })

  it("renders wallet summaries and falls back safely for malformed structured data", async () => {
    const walletView: TaskViewResponse = {
      kind: "wallet_state",
      data: {
        accounts: [
          { id: "cash", name: "Cash", currency: "USD", balance_minor: 8750 },
          { id: "wallet", name: "Pesos", currency: "ARS", balance_minor: 7000 },
        ],
        totals_by_currency: [
          { currency: "ARS", balance_minor: 7000 },
          { currency: "USD", balance_minor: 8750 },
        ],
      },
      available_actions: [],
    }
    const wallet = buildTurnResponse({
      active: false,
      taskView: walletView,
      outcome: {
        kind: "state_shown",
        message: "Current balances.",
        view: walletView,
      },
    })
    const malformedView: TaskViewResponse = {
      kind: "wallet_state",
      data: { accounts: "invalid", totals_by_currency: [] },
      available_actions: [],
    }
    const malformed = buildTurnResponse({
      version: 2,
      active: false,
      taskView: malformedView,
      outcome: { kind: "state_shown", message: "Still available.", view: malformedView },
    })
    mockTurnResponses(wallet, malformed)
    const user = userEvent.setup()
    renderApp("/assistant")

    await user.click(await screen.findByRole("button", { name: "Show my current balances" }))
    expect(await screen.findByLabelText("Wallet balances")).toBeInTheDocument()
    expect(screen.getByText("USD 87.50")).toBeInTheDocument()
    expect(screen.getAllByText("ARS 70.00").length).toBeGreaterThan(0)

    await user.type(screen.getByLabelText("Message the wallet"), "Balances again{enter}")
    expect(await screen.findByText("Still available.")).toBeInTheDocument()
    expect(screen.getAllByText("Details").length).toBe(2)
  })

  it("retries a failed turn with the identical request", async () => {
    const submit = vi.spyOn(TurnsService, "turnsSubmitConversationTurn")
    submit
      .mockRejectedValueOnce({ detail: "Conversation processing is temporarily unavailable." })
      .mockResolvedValueOnce(buildSuccess(buildTurnResponse()))
    const user = userEvent.setup()
    renderApp("/assistant")

    await user.type(await screen.findByLabelText("Message the wallet"), "Record an expense{enter}")
    expect(
      await screen.findByText("Conversation processing is temporarily unavailable."),
    ).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Retry safely" }))
    await screen.findByText(/Ready to record:/)

    expect(submit.mock.calls[1][0].body).toEqual(submit.mock.calls[0][0].body)
    expect(screen.getAllByText("Record an expense")).toHaveLength(1)
  })

  it("restores a tab session and clears it when the server conversation expired", async () => {
    const conversation = buildConversation()
    sessionStorage.setItem(
      SESSION_KEY,
      JSON.stringify({
        version: 1,
        transcript: [
          { id: "user-1", role: "user", label: "Record an expense" },
          {
            id: "assistant-1",
            role: "assistant",
            outcome: {
              kind: "preview",
              message: "Restored preview.",
              view: captureView(),
            },
            conversationVersion: 1,
            taskId: "task-1",
            taskVersion: 1,
          },
        ],
        conversation,
        pending: null,
      }),
    )
    vi.spyOn(ConversationsService, "conversationsGetConversation").mockRejectedValue({
      detail: "conversation not found: conversation-1",
    })
    renderApp("/assistant")

    expect(
      await screen.findByText(/previous chat expired after the server restarted/i),
    ).toBeInTheDocument()
    expect(screen.queryByText("Restored preview.")).not.toBeInTheDocument()
    expect(screen.getByLabelText("Message the wallet")).toBeEnabled()
  })

  it("restores an available conversation and its current actions", async () => {
    const conversation = buildConversation()
    sessionStorage.setItem(
      SESSION_KEY,
      JSON.stringify({
        version: 1,
        transcript: [
          { id: "user-1", role: "user", label: "Record an expense" },
          {
            id: "assistant-1",
            role: "assistant",
            outcome: {
              kind: "preview",
              message: "Restored preview.",
              view: captureView(),
            },
            conversationVersion: 1,
            taskId: "task-1",
            taskVersion: 1,
          },
        ],
        conversation,
        pending: null,
      }),
    )
    const read = vi
      .spyOn(ConversationsService, "conversationsGetConversation")
      .mockResolvedValue(buildSuccess(conversation))
    renderApp("/assistant")

    expect(await screen.findByText("Restored preview.")).toBeInTheDocument()
    await waitFor(() => expect(read).toHaveBeenCalledOnce())
    expect(screen.getByRole("button", { name: "Confirm" })).toBeEnabled()
    expect(screen.getByRole("button", { name: "Cancel" })).toBeEnabled()
  })

  it("refreshes authoritative state after a stale action", async () => {
    const submit = vi.spyOn(TurnsService, "turnsSubmitConversationTurn")
    submit
      .mockResolvedValueOnce(buildSuccess(buildTurnResponse()))
      .mockRejectedValueOnce({ detail: "turn target or conversation version is stale" })
    const refreshedView = captureView({
      available_actions: [confirmOffer({ expected_conversation_version: 2 })],
    })
    const refreshed = buildConversation({ version: 2, taskView: refreshedView })
    vi.spyOn(ConversationsService, "conversationsGetConversation").mockResolvedValue(
      buildSuccess(refreshed),
    )
    const user = userEvent.setup()
    renderApp("/assistant")

    await user.type(await screen.findByLabelText("Message the wallet"), "Record an expense{enter}")
    await screen.findByText(/Ready to record:/)
    await user.click(screen.getByRole("button", { name: "Confirm" }))

    expect(
      await screen.findByText(
        "This action is no longer current. Continue from the latest assistant response.",
      ),
    ).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText("Conversation v2")).toBeInTheDocument())
    expect(screen.queryByRole("button", { name: "Retry safely" })).not.toBeInTheDocument()
  })

  it("recovers a pending request after refresh and supports New chat", async () => {
    const request = {
      request_id: "stable-request-id",
      input: { kind: "message" as const, content: "Record an expense" },
    }
    sessionStorage.setItem(
      SESSION_KEY,
      JSON.stringify({
        version: 1,
        transcript: [{ id: "user-1", role: "user", label: "Record an expense" }],
        conversation: null,
        pending: { request, label: "Record an expense" },
      }),
    )
    const submit = mockTurnResponses(buildTurnResponse())
    const user = userEvent.setup()
    renderApp("/assistant")

    expect(await screen.findByText(/may have completed before the page refreshed/i)).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Retry safely" }))
    await screen.findByText(/Ready to record:/)
    expect(submit.mock.calls[0][0].body.request_id).toBe("stable-request-id")

    await user.click(screen.getByRole("button", { name: "New chat" }))
    expect(screen.getByText("What would you like to do?")).toBeInTheDocument()
    expect(screen.queryByText(/Ready to record:/)).not.toBeInTheDocument()
    expect(sessionStorage.getItem(SESSION_KEY)).toBeNull()
  })
})
