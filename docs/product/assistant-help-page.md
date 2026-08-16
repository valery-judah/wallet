# Wallet Assistant Help Page

Status: proposed

## Purpose

Add a small, user-facing Help page for the Wallet Assistant. The page should explain what the

assistant can do, show useful example requests, document the exact conversation controls, and

set expectations for an active transaction workflow.

This is product help, not an API or architecture reference. It should use the same language as

the chat UI and avoid capability IDs, route-decision names, request IDs, versions, prompts, and

other implementation details.

## Product Decision

Help should be a static page at `/assistant/help`, not another conversation turn.

- The existing Help button opens the page without calling the conversation API.
- The page includes a clear **Back to Assistant** action.
- Typing an exact `help` or `what can you do` message in chat remains supported and returns the
  short in-conversation capability summary.
- The Help page is not a separate sidebar destination. **Assistant** remains the selected
  sidebar section while the page is open.
- Opening and closing Help must preserve the current transcript, conversation, active task, and
  unsent draft.

The distinction is intentional: the page teaches the complete interaction model, while the

chat command provides a brief answer without leaving the conversation.

## Information Architecture

The page uses one narrow content column and presents sections in this order.

### 1. Header

- Back link: **Back to Assistant**
- Title: **How to use Wallet Assistant**
- Description: **Ask about your balances or describe a transaction in everyday language.**
- Primary action: **Open Assistant**

The primary action and back link both return to `/assistant` without resetting the chat.

### 2. What You Can Ask

Show five compact example cards. Each card names the supported job and includes one realistic

message.

| Job | Example message |
| --- | --- |
| Check balances | `Show my current balances` |
| Record an expense | `I spent ARS 4,500 at the supermarket from Cash yesterday` |
| Record income | `I received ARS 120,000 salary into Main account today` |
| Record a transfer | `Move ARS 10,000 from Main account to Cash` |
| Adjust a balance | `Set Cash balance to ARS 25,000` |

Examples are instructional, not quick-reply buttons in the first version. This avoids implying

that the example will be sent immediately or that its account and category names exist in the

user's wallet.

### 3. Conversation Controls

Explain that a control must be the entire message. Matching is case-insensitive, ignores extra

whitespace, and permits trailing `.`, `?`, or `!` punctuation. For example, `Cancel!` is a

control, while `cancel my membership` is an ordinary message.

| Control | Accepted messages | When to use it | Result |
| --- | --- | --- | --- |
| Help | `help`, `what can you do` | At any time | Shows a short capability summary and preserves the current task |
| Cancel | `cancel`, `stop`, `never mind` | While a task is active | Ends the current task without recording its unfinished transaction |
| Restart | `restart`, `start over` | While a task is active | Discards the current draft and starts that task again |

The page should also distinguish the UI-only **New chat** action:

- **New chat** clears this tab's transcript and current conversation.
- It is not a message command and should not be presented in the exact-command table.

### 4. While Recording a Transaction

Use a highlighted guidance panel with the following interaction model:

1. Describe the transaction with as much information as is convenient.
2. Answer follow-up questions in the composer. When choices are shown, type the matching label.
3. Review the transaction draft.
4. Use the displayed **Confirm** button to record it.

Include this important ownership rule:

> While a transaction task is active, ordinary messages belong to that task. To ask for
> balances or begin different work, cancel the current task first.

Do not suggest that typing `yes` is equivalent to the guarded **Confirm** action. Confirmation

is represented by the action offered beneath the latest assistant response.

### 5. Good to Know

Keep operational guidance short and user-oriented:

- The assistant handles one request at a time.
- Your chat is kept in this browser tab and survives a refresh, but it is not durable history.
- A server restart can expire the current conversation; the UI will ask you to start again.
- A transaction is not recorded until the **Confirm** action succeeds.
- Balance requests are read-only.

Do not expose Ollama configuration on this page. If the language service is unavailable, the

chat's existing error and retry experience is the appropriate explanation.

## Layout and Responsive Behavior

Desktop:

- Use the existing application shell and sidebar.
- Constrain content to a readable width of approximately `48rem` to `56rem`.
- Display example cards in two columns, with the final card spanning naturally or remaining a
  single card.
- Render commands as stacked rows or cards so accepted phrases and results remain scannable.

Mobile:

- Collapse all content to one column.
- Keep the back action at the top of the page.
- Wrap command phrases rather than introducing horizontal scrolling.
- Do not use a dense desktop-style table when it would require side-to-side scrolling.

The page should reuse existing typography, borders, cards, buttons, muted text, and primary

color. It does not need illustrations, screenshots, search, tabs, accordions, or a table of

contents.

## Navigation and Chat State

The existing Assistant Help button currently submits a typed Help control. Replace that button

behavior with navigation to `/assistant/help`.

Because the Assistant route unmounts during navigation, the stored Assistant session should

also retain the unsent composer draft. Evolve the versioned session shape safely so an existing

version-1 session restores with an empty draft rather than being discarded. Returning from Help

must not create a user message, increment the conversation version, invoke the message router,

or change the active task.

Textual Help remains a normal deterministic control submission. This preserves non-UI clients

and gives chat users a concise answer when they type the command directly.

## Accessibility and Copy

- Use semantic heading order beginning with one `h1`.
- Give navigation actions descriptive accessible names.
- Do not rely on icons alone for Back, Help, or Open Assistant actions.
- Present accepted commands as text, not as disabled buttons.
- Keep examples selectable and copyable.
- Use **task** and **transaction draft** in user-facing copy; do not use **capability** or
  **workflow session**.
- Prefer direct instructions such as **Cancel the current task first** over explanations of the
  internal router.

## Out of Scope

- Sending an example from the Help page
- Search or command filtering
- Context-sensitive Help content based on the active task
- Backend changes to the Help outcome
- Model, prompt, routing, or logging documentation
- Durable conversation history
- Additional controls or transaction capabilities

## Acceptance Criteria

1. `/assistant/help` renders inside the existing application shell and keeps Assistant selected
   in the sidebar.
2. The Assistant Help button navigates to the page without submitting a turn.
3. Back to Assistant restores the same transcript, conversation, active task, and unsent draft.
4. The page documents all five supported user jobs and all seven accepted exact control phrases.
5. The page clearly states that controls must be whole messages.
6. The page explains active-task ownership and instructs users to cancel before starting
   different work.
7. The transaction guidance uses the displayed Confirm action and never promises that textual
   confirmation will execute a transaction.
8. The page works without horizontal scrolling at mobile widths.
9. Opening and closing Help causes no conversation API request and no Wallet data mutation.
10. Existing typed and textual Help behavior remains covered by backend tests.

## Suggested Frontend Tests

- Opening Help from an idle chat performs navigation and submits no turn.
- Opening Help during an active task preserves the task after returning.
- An unsent composer draft survives the Help round trip.
- A stored version-1 Assistant session migrates with an empty draft.
- The page exposes the supported-job headings, exact command phrases, and active-task guidance.
- Back to Assistant and Open Assistant both return to the chat without clearing it.
- The Help page remains readable at the frontend test suite's mobile viewport.
