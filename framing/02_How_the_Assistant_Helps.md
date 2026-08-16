# How a conversational agent could help with each problem

This is the second framing artifact. For each problem in [Problems](01_Problems.md) it describes how conversation could help, what has to exist outside the language model, what the assistant must not do, and **how much conversation helps** (its leverage). It ends with a map that combines leverage with criticality, to find the problems where a conversational agent helps most.

## Where conversation has leverage in money tracking

Conversation helps most in six situations:

| # | Source of leverage | Why conversation | Problems |
| --- | --- | --- | --- |
| **C1** | **The person knows what the data does not** | Purpose, who a payment was for, what a receipt contained, which payment is missing. Only the person has this, and a short dialog is the cheapest way to get it. | W2, W3, W4, W7, W9, W17 |
| **C2** | **Turning intent into structure** | "Paid 60 for dinner with Ana from cash, half is hers" becomes an expense, a split, and an amount owed, without the person learning the schema. | W1, W4, W5, W17 |
| **C3** | **Asking only what matters** | One targeted question instead of a form or a review queue of everything. | W2, W3, W8 |
| **C4** | **Questions in the person's own words** | Totals, causes, and comparisons without navigating screens. | W10, W12, W13 |
| **C5** | **Working through a process together** | Reconciliation, catching up, setup: step by step, keeping state between steps. | W7, W9, W14, W15 |
| **C6** | **Tone and scope** | A calm, non-judgmental way in, one thing at a time. | W16 |

Conversation is weak at:

- arithmetic and totals;
- knowing whether data is complete or current;
- applying the same rule every time;
- privacy;
- speed when a direct view is faster;
- avoiding confident wrong answers.

These stay in deterministic code or the interface.

## Principles

1. **The model interprets; the ledger decides.** Balances, totals, and validity come from deterministic code. This principle from the earlier AI frame (WF) still holds.
2. **Every answer shows its evidence:** which entries, which period, what was excluded, and how it was calculated (CR hypotheses H1 and H2).
3. **Ask only when the answer changes something important.** Use the amount, the effect on totals, and the confidence of the interpretation (ST: "reconcile exceptions, not the whole ledger").
4. **Propose, then confirm.** No write without an explicit confirmation that shows the effect first. Competitors have converged on this, and WF requires it.
5. **Optional and faster than the alternative.** Conversation is one way in, never in the way (W19).
6. **Neutral language.** No failure framing; one thing at a time (W16).
7. **Minimal data to the model.** Wallet's local model (Ollama) is already an advantage for W18.

## Kinds of help

| Kind | What it means | Example |
| --- | --- | --- |
| **Capture** | Turns a description into a reviewable entry | "40 at the pharmacy from Mercado Pago" |
| **Clarify** | Asks the one question that changes the record | "This 900 from your bank to Wise: a transfer between your own accounts?" |
| **Reconcile** | Works with the person until the record matches reality | "Cash shows 12,000 and you have 9,500. Let's find the 2,500." |
| **Answer** | Answers from the ledger, with the evidence | "The trip cost 1,840 USD across 23 entries. Show them?" |
| **Organize** | Changes many entries, or the categories, from one instruction, with a preview | "Mark all Uber rides in March as work, reimbursable." |
| **Re-engage** | Helps the person return after a gap without cleaning up everything | "Nothing recorded since October 3. Want to do a rough catch-up?" |

## Problem by problem

**Leverage**:

- **very high**: conversation is the best way to solve the problem;
- **high**: conversation clearly helps;
- **medium**: it helps, but code or the interface does most of the work;
- **constraint**: not a conversation feature; a rule the assistant must respect.

The C codes say where the leverage comes from.

### A. Keeping the record current

| Problem | How the assistant helps | Needed outside the model | Must not | Leverage |
| --- | --- | --- | --- | --- |
| **W1** Recording is too much work | Captures entries from a short description at the moment of payment, accepts shorthand, asks only for missing fields, and can take several payments in one message. | Ledger validation; confirmation; account and category aliases; a fast model | Record without confirmation; take more turns than the form; record a payment twice when a message is repeated | high (C2), if it is faster than the form |
| **W2** Where, not why | Asks "what was it for?" at capture time or later for unexplained entries, starting with large or ambiguous ones. Learns the person's own words for each merchant. | A place to store purpose beyond one category; rules learned from confirmed answers | Guess the purpose silently; ask about every small payment | **very high** (C1, C3): only the person knows |
| **W3** Transfers and refunds miscounted | Recognizes likely transfers, refunds, reimbursements, and card repayments from the description ("got 37.50 back from the shoe store") and asks one question that shows the effect on totals. | Transaction types with correct ledger meaning (Wallet already separates expense, income, transfer, and adjustment); refund links; matching pairs | Choose the type silently when the effect on totals differs | high (C1, C3) |
| **W4** One payment, several things | "Amazon 93: what was in it?" → a split by category; "half is Ana's" → a shared part. | The ledger already allows one expense across several categories; shared parts need ownership; a check that the parts add up | Invent amounts for the parts; leave a remainder unassigned | high (C1, C2) |
| **W5** Categories don't fit | The person describes how they think about their money; the assistant proposes categories or tags in their words and maps old categories when they change. | Category trees (exist); tags or attributes beyond one category (do not exist) | Restructure without a preview; rewrite history | medium (C2) |

### B. Keeping the record true

| Problem | How the assistant helps | Needed outside the model | Must not | Leverage |
| --- | --- | --- | --- | --- |
| **W6** Complete and current? | Answers "is this complete?" from computed data status; asks about suspicious gaps ("no cash spending for 9 days: normal?"). | Data status in code: last entry per account, gaps, unconfirmed entries | Present totals as complete when there are gaps | medium (C1 for gaps; the status itself is code) |
| **W7** Balance doesn't match reality | Guided reconciliation. The person gives the real balance. The assistant shows the difference and walks through likely causes (recent days, typical missing kinds such as cash and small card payments). It records what is found, and only then offers a labeled adjustment for the rest. | Difference calculation; lists of candidate periods; adjustment as an explicit correction (exists) | Jump straight to an adjustment that hides missing entries; invent transactions to make the numbers match | **very high** (C1, C5) |
| **W8** Fixing accumulated errors | Bulk changes from one instruction, with a preview ("all Uber in March → Work"); offers to turn it into a rule; reviews only exceptions. | Bulk editing with preview and undo; rules | Change entries outside the described set; apply without a preview | high (C2, C3) |
| **W9** Catching up after a break | Catch-up interview since the last entry: records the big payments it can recall, makes a rough estimate for the rest ("about how much cash per week?"), and labels the estimate as such. A fresh start without cleaning up everything. | Gap detection; estimate entries or adjustments that stay visibly marked as estimates | Present estimates as recorded facts; shame the gap | **very high** (C1, C5, C6) |

### C. Understanding

| Problem | How the assistant helps | Needed outside the model | Must not | Leverage |
| --- | --- | --- | --- | --- |
| **W10** Simple questions need digging | Answers questions in the person's words and handles follow-ups ("and without the hotel?"). | A deterministic query layer; the list of entries behind each answer | Calculate totals in the model; answer from general knowledge | high (C4), but competitors already offer it |
| **W11** Can't trust an answer | Every answer comes with included and excluded entries, the period, the calculation, and assumptions the person can change in words ("exclude reimbursed meals"). | Deterministic queries with an evidence set; data status | Give a number without its basis; sound more certain than the data | high, conditional: conversation creates this problem, evidence solves it, and conversation makes assumptions easy to change |
| **W12** Why did my balance change? | Explains a change by tracing its causes ("cash is 300 lower: half of the rent, two taxi rides, …") in plain language. | Change breakdown computed in code | Judge or advise ("you overspent") | high (C4) |
| **W13** Forgotten recurring charges | When a recurring payment is captured, asks whether it repeats; lists recurring items with their yearly cost; runs a "keep or drop?" review and checks next month whether a dropped charge stopped. | Recurring items and schedules in code | Cancel anything itself (outside the wallet); push savings advice | medium (C3, C4) |

### D. The money map

| Problem | How the assistant helps | Needed outside the model | Must not | Leverage |
| --- | --- | --- | --- | --- |
| **W14** Many places and currencies | Builds the money map by conversation ("USD cash, a Wise account, Mercado Pago…"); answers per currency without false totals. | Accounts per currency (exists); no conversion unless an exchange-rate model exists | Add up different currencies | medium (C2, C5) |
| **W15** Setup and switching | A setup interview; maps categories when switching ("your 'Eating out' → 'Dining'?"); previews what will be imported. | An importer (does not exist); mapping storage; a dry run that reconciles counts and totals | Import without a preview | high for setup (C5); medium for switching |

### E. People and feelings

| Problem | How the assistant helps | Needed outside the model | Must not | Leverage |
| --- | --- | --- | --- | --- |
| **W16** Anxiety and avoidance | Lowers the threshold: one thing at a time, neutral words, the person chooses how much to look at; a quick "anything that needs attention?". | No failure states in the interface; style preferences | Judge; flood with warnings; raise money topics the person did not ask about | high (C6), with care |
| **W17** Shared money | Captures shared expenses in words ("paid 60, half is Ana's"), keeps track of who owes whom, answers "how much does Ana owe me?". | People, ownership, and amounts owed (do not exist; WF excludes shared households today) | Show one person's private entries to another | high (C1, C2), later |

### F. Trust in the product

| Problem | How the assistant helps | Needed outside the model | Must not | Leverage |
| --- | --- | --- | --- | --- |
| **W18** Data feels risky | Explains what data the assistant sees and keeps. | The local model; minimal context per call; control over how long transcripts are kept | Send data to remote services; keep transcripts longer than needed | constraint |
| **W19** AI in the way, or slower | None: it must stay optional and quick. | Every job doable without the assistant; a latency budget | Block or cover the main interface | constraint |

## Where conversation helps most

Criticality comes from [Problems](01_Problems.md); leverage from the tables above.

| Criticality \ Leverage | Very high | High | Medium | Constraint |
| --- | --- | --- | --- | --- |
| **High** | W7, W9 (high for manual), W2 | W1, W3, W11, W16 | W6 | W18 |
| **Medium** | — | W4, W8, W10, W12, W15, W17 | W5, W13, W14 | W19 |

**The strongest set is W2, W3, W7, and W9.** They share one mechanism: the person holds information the record lacks (why, what kind of movement, which payment is missing, roughly what happened during a gap), and a short dialog is the cheapest way to get it. Competitors put their assistants into question answering and automated cleanup of synced data, so this use of conversation is less contested.

The rest of the high-criticality group:

- **W1** is where the current Wallet assistant already works. Its value depends on being faster than the form.
- **W11** is a condition rather than a feature. Any answering capability must solve it, or conversation makes the product less trustworthy.
- **W16** has high leverage but needs careful design, because it shapes how every other feature talks.

**W10** is high leverage but commodity: necessary, not differentiating.

## Where the assistant could make things worse

These are anticipated risks, not observed failures. They can guide which cases to write, and some may become checks for repeated assessment. Whether they occur, and which failures nobody anticipated, is for review of real traces to show.

| Risk | Example | Problems |
| --- | --- | --- |
| Confident wrong totals | A fluent answer that hides a wrong selection of entries | W10, W11 |
| Silent wrong meaning | A transfer recorded as spending | W3 |
| Too many questions | Asking about a 3.20 coffee | W2, W3, W8 |
| Slower than the form | Several turns for one simple payment; a slow local model | W1, W19 |
| Estimates that look like facts | A catch-up estimate or an adjustment that hides missing entries | W7, W9 |
| Duplicates | A repeated message records the same payment twice (the situation is exercised by wallet-evals case T020) | W1 |
| Judgmental tone | "You overspent on restaurants again" | W16 |
| Memory it does not have | "As you told me last month…" without stored context | W11 |
| Sensitive transcripts | Conversation history kept or sent elsewhere | W18 |

## What the current Wallet assistant covers

Today the assistant does two things:

- captures one transaction from a description, with follow-up questions and confirmation;
- reports current balances, separated by currency.

That addresses **W1** and part of **W10** and **W14**.

The highest-leverage problems have no assistant support yet:

- **W2**: asking why for entries that lack a purpose;
- **W3**: beyond choosing the type at capture time;
- **W7**: reconciliation beyond a single adjustment;
- **W9**: catching up after a gap;
- **W11**: evidence behind answers.

The product also lacks the data those problems need:

- purpose or tags beyond one category;
- recurring items;
- data status;
- import;
- people and ownership.

## Summary

| Leverage | Problems |
| --- | --- |
| very high | W2, W7, W9 |
| high | W1, W3, W4, W8, W10, W11, W12, W15, W16, W17 |
| medium | W5, W6, W13, W14 |
| constraint | W18, W19 |
