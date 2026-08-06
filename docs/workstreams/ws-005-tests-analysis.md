## Assessment

The suite is strong as a deterministic software test suite, but it is not yet an AI evaluation suite.

There are 104 collected tests under `backend/tests/ai/transaction_capture/`; all pass. Including the smoke-runner tests gives 119 passing tests. However, most model outputs are scripted, so they prove that the application safely processes a particular structured response—not that the model reliably produces that response from realistic user language.

### Coverage by layer

| Layer | Assessment | What is covered |
|---|---|---|
| Candidate/session invariants | Strong | Required fields, type changes, invalid values, terminal sessions |
| Workflow and execution | Strong | Progressive capture, validation, one-time execution, wallet failures |
| Grounding | Strong but narrow | Exact labels, category ambiguity, supported numeric/date formats |
| Extraction | Contract coverage only | Anchoring, retry, schema errors using predetermined model output |
| Semantic interpretation | Contract coverage only | Evidence references, incompatible fields, clears, prompt privacy |
| Real-model behavior | Weak | Six manual smoke scenarios with clean English inputs |
| Evaluation dataset | Missing | No coverage metadata, balancing, aggregate metrics, or regression corpus |

The distinction is visible in [test_extraction.py](/Users/val/projects/ps/wallet/backend/tests/ai/transaction_capture/test_extraction.py:41) and [test_semantic.py](/Users/val/projects/ps/wallet/backend/tests/ai/transaction_capture/test_semantic.py:60): the tests prescribe what the fake model returns. By contrast, the actual model smoke surface contains only six scenarios in [scenarios.py](/Users/val/projects/ps/wallet/backend/scripts/devex/transaction_capture_smoke/scenarios.py:55).

## Highest-priority gaps

1. **Currency can be silently discarded.** Monetary grounding extracts only the numeric value in [grounding.py](/Users/val/projects/ps/wallet/backend/src/wallet/ai/transaction_capture/grounding.py:202), while execution uses the selected account’s currency. “Spent $40 from Daily checking” could therefore become an ARS 40 expense instead of requiring clarification. This is an execution-boundary safety issue.

2. **Common monetary language is unsupported.** `2,500`, `1.000`, `forty-five`, and similar forms are not accepted by the deterministic normalizer. The smoke input deliberately uses `2500 pesos`, although the historical use case uses `$2,500`.

3. **Date coverage is very narrow.** Only `today`, `yesterday`, `tomorrow`, and ISO dates are normalized in [grounding.py](/Users/val/projects/ps/wallet/backend/src/wallet/ai/transaction_capture/grounding.py:213). Inputs such as “last Friday,” “on the 3rd,” or “two days ago” should be explicitly classified as supported or clarification-required.

4. **Real-model multi-turn coverage is almost entirely expense-centric.** There is no progressive income, transfer correction, negative adjustment, type change, metadata correction, or unrelated-answer scenario.

5. **Unsupported requests lack evaluation coverage.** Split expenses, multiple transactions in one message, refunds, editing, cancellation, and capture interruption must at minimum prove that no incorrect transaction is recorded.

6. **Model quality is not measured.** The traces contain useful intermediate state, but there is no dataset runner producing field accuracy, clarification quality, or unsafe-execution metrics.

## Recommended dimensions

I would not use “user persona” initially: nothing in the current product changes behavior by user type. These dimensions correspond more directly to failure surfaces:

| Dimension | Values |
|---|---|
| Intent | Expense, income, transfer, adjustment, unsupported workflow |
| Dialogue shape | One-shot, progressive, correction, clear, interruption |
| Input quality | Complete, incomplete, ambiguous, contradictory, noisy |
| Expression form | Canonical, conversational, shorthand, typo, locale-formatted, words |
| Reference state | Exact, full path, ambiguous leaf, missing, archived, duplicate, cross-currency |
| Required action | Execute, request value, disambiguate, correct, clarify, do not execute |

Fixtures should remain separate from dimensions: wallet catalog, current date, duplicate category labels, archived accounts, currencies, and existing session state.

## Initial 24-case user-query set

This is an initial manually reviewed set, not 24 paraphrases of the same happy path.

| ID | Target interaction | User input or sequence | Expected condition |
|---|---|---|---|
| Q01 | Complete expense | “Spent 40 pesos from Daily checking on Groceries yesterday.” | Correct expense executes once |
| Q02 | Complete income | “Received 2500 pesos as Payroll into Daily checking today.” | Correct income executes once |
| Q03 | Complete transfer | “Move 100 pesos from Daily checking to Pocket wallet.” | Correct transfer executes once |
| Q04 | Positive adjustment | “Increase USD cash by 50 dollars.” | `+5000 USD` adjustment |
| Q05 | Negative adjustment | “Reduce USD cash by 20 dollars.” | `-2000 USD` adjustment |
| Q06 | Progressive expense | “Record an expense.” → “35” → “Pocket wallet” → “Coffee” | Stable question order; one execution |
| Q07 | Rich follow-up | “Record an expense.” → “35 pesos from Pocket wallet for Groceries” | All supplied fields applied together |
| Q08 | Progressive transfer | “Transfer 100 pesos from Daily checking.” → “Pocket wallet” | Destination resolved contextually |
| Q09 | Correction | “Spent 25 pesos from Pocket wallet on Coffee.” → “Actually, use Daily checking” | Account replaced before execution |
| Q10 | Type change | “Spent 100 pesos from Daily checking.” → “Actually this was a transfer to Pocket wallet” | Expense-only state removed; transfer state used |
| Q11 | Optional metadata | “Spent 25 pesos from Pocket wallet on Restaurants at Corner Cafe. Team lunch.” | Merchant/description preserved |
| Q12 | Metadata clear | Start an incomplete expense with notes → “Remove the note” | Note cleared using explicit evidence |
| Q13 | Ambiguous category | With `Food > Coffee` and `Work > Coffee`: “Spent 35 pesos from Pocket wallet on Coffee.” | Disambiguation; no execution |
| Q14 | Full category path | Same fixture: “Spent 35 pesos from Pocket wallet on Food > Coffee.” | Exact path executes without ambiguity |
| Q15 | Unknown reference | “Spent 35 pesos from Mystery account on Groceries.” | Account correction; no execution |
| Q16 | Archived account | “Spent 35 pesos from Old travel card on Groceries.” | Archived account unavailable; no execution |
| Q17 | Same-account transfer | “Transfer 100 pesos from Pocket wallet to Pocket wallet.” | Destination correction; no execution |
| Q18 | Cross-currency transfer | “Transfer 100 pesos from Daily checking to USD cash.” | Currency conflict; no execution |
| Q19 | Thousands separator | “Received 2,500 pesos as Payroll into Daily checking.” | Should mean 250,000 minor units, or explicitly clarify |
| Q20 | Amount in words | “I spent forty pesos from Pocket wallet on Coffee.” | Supported interpretation or safe clarification; never wrong execution |
| Q21 | Nontrivial date | “Spent 40 pesos from Daily checking on Groceries last Friday.” | Resolve per declared policy or clarify; do not default silently |
| Q22 | Currency/account mismatch | “Spent $40 from Daily checking on Groceries.” | Must not silently record ARS 40 |
| Q23 | Split expense | “Spent 100 pesos from Daily checking: 70 on Groceries and 30 on Household Items.” | No single-category transaction |
| Q24 | Multiple/unsupported action | “Record 20 pesos for Coffee and delete the expense I added yesterday.” | Do not collapse into one new transaction or edit history |

Add cancellation, unrelated replies, prompt injection, Spanish, and noisy speech-like inputs once their product boundary is explicitly decided.

## Suggested 100-execution allocation

- 24 clean core-intent cases
- 20 progressive and correction cases
- 20 grounding and wallet-state cases
- 16 money/date/language-form cases
- 14 unsupported and safety cases
- 6 exploratory locale or known-hard regression cases

The primary metric should be **incorrect automatic execution rate**, with a target of zero for ambiguous, contradictory, invalid, and unsupported cases. Secondary metrics should include correctly recorded transaction rate, per-field accuracy, joint candidate accuracy, appropriate-clarification rate, unnecessary-question rate, and turns to completion.

The existing smoke runner is a good foundation: retain its fresh-wallet isolation and typed posting assertions, but make cases data-driven and record tuple metadata, fixtures, model version, prompts, complete traces, latency, and failure classification. No repository files were changed.