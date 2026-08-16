# Problems people have keeping track of their money

This is the first framing artifact for a conversational agent in Wallet. Scope: **the wallet**, meaning recording money movements, keeping the record true, and understanding it. Planning and advice (bills, forecasts, goals) belong to a later financial assistant. Their problems are listed separately at the end, because the research ranks them as the most critical money problems and they depend on a reliable wallet.

The existing product frames ([product frame](../docs/product/wallet-frame.md), [AI capabilities frame](../docs/product/ai-capabilities-frame.md), [MVP spec](../docs/product/spec.md)) come from an earlier MVP. They are used here as input, not as constraints.

## Sources

Paths are relative to the `financial-apps/` research notes folder, which is kept outside this repository.

| Key | Document | Kind of evidence |
| --- | --- | --- |
| **ST** | `problems-with-spend-trackers-deep-research.md` | HCI studies, vendor support documentation, behavioral research |
| **PL** | `financial-problems-money-tracker-planner-apps.md` | Federal Reserve, CFPB, and Census surveys; industry surveys; app reviews |
| **CR** | `competitive-research-personal-finance-assistants.md` | Documentation and user reports for Monarch, Copilot, Simplifi, Origin, Rocket Money |
| **CG** | `chatgpt-finances-trust-report.md` | Public reaction to ChatGPT Finances; a privacy survey; expert commentary |
| **MK** | `market-context/market.md`, `market-context/context.md` | Working model of user jobs |
| **HH** | `housholds-helper.md` | Market scan of personal financial agents and household models |
| **WF** | Wallet product frames, linked above | Product hypotheses from the earlier MVP, not user evidence |

## Ratings

- **Evidence** follows the sources' own ratings:
  - **strong**: representative surveys, peer-reviewed research, or consistent vendor documentation;
  - **moderate**: the mechanism is established but prevalence is uncertain; small studies; industry surveys;
  - **weak**: app reviews, forums, single reports;
  - **hypothesis**: an inference not yet checked.
- **Criticality**: how much the problem harms the person or the trustworthiness of the record, and how often it is likely to occur (high, medium, low).
- **Applies to**:
  - **manual**: the person records entries;
  - **connected**: entries are imported from banks;
  - **both**.

  Wallet is manual today; many of the strong findings come from connected trackers.
- **Who**: the user jobs from MK that the problem affects most.
  - **R**: reassurance seeker;
  - **I**: intentional spender;
  - **G**: goal builder;
  - **O**: optimizer;
  - **A**: avoider or resetter;
  - **S**: stabilizer;
  - **H**: household (overlay);
  - **V**: variable income (overlay);
  - **M**: money in many places and currencies. M is Wallet's own target context from WF, not an MK job.

## A. Keeping the record current

| # | Problem, in the user's words | What is underneath | Evidence | Criticality | Applies to | Who |
| --- | --- | --- | --- | --- | --- | --- |
| **W1** | "Recording every payment is too much work." | Manual entry costs time at the wrong moment. Automatic import does not remove the work; it turns entry into review and repair. People abandon tracking when the effort exceeds the value. | strong (ST, PL) | high | both | all |
| **W2** | "The record says where money went, not why." | A payment has an amount, a date, and a merchant. The purpose often exists only in the person's head: what an Amazon order contained, what a PayPal charge was for, whether +37.50 is a refund. In one small 2016–17 dataset, 28% of bank transactions arrived uncategorized. Better automatic categorization has a ceiling. | strong (ST) | high | both: imported records lack the purpose; manual records lose it if it is not captured at the moment | R, I, O |
| **W3** | "Transfers, refunds, and repayments get counted as spending or income." | Movements between one's own accounts, refunds, reimbursements, credit-card repayments, and payment intermediaries such as PayPal distort totals or count the same money twice. | strong (ST: vendor documentation) | high | both | all, especially H, M |
| **W4** | "One payment is really several things." | One receipt covers food and household goods; one dinner is partly someone else's; one charge is partly reimbursable. A single category forces a false choice. | strong (ST; CR: split defects in Simplifi's assistant) | medium | both | I, H, O |
| **W5** | "The categories don't match how I think about money." | Fixed monthly categories fit poorly with irregular costs and household practices. One category cannot carry purpose, ownership, reimbursement, and recurrence at once. Vendors are adding more flexible models. | moderate (ST: CHI study of 15 households; vendor changes) | medium | both | I, H, V |

## B. Keeping the record true

| # | Problem | What is underneath | Evidence | Criticality | Applies to | Who |
| --- | --- | --- | --- | --- | --- | --- |
| **W6** | "I can't tell whether the numbers are complete and current." | Connected: delayed syncs, missing pending transactions, duplicates. Manual: forgotten cash payments and days without entries. Either way, the interface looks more certain than the data. | strong for connected (ST); hypothesis for manual | high | both | R, O |
| **W7** | "My balance doesn't match reality, and finding out why is tedious." | Reconciliation means hunting for missing or wrong entries. A blanket correction fixes the number but can hide a missing transaction. Monarch lacks conventional reconciliation between manual and synced entries. | moderate (ST, CR; an open question in WF) | high | both | R, M |
| **W8** | "Fixing accumulated errors takes too long." | The person becomes the repair layer: recategorizing the same merchant every month, merging duplicates, maintaining rules. Many assistant errors start in this messy state. | weak for prevalence, consistent across reviews (PL, CR) | medium | both, mainly connected | O, H |
| **W9** | "I stopped recording for a while; catching up feels like starting over." | A manual record decays as soon as recording lapses. The gap makes every later balance doubtful, and having to clean up everything first is a barrier to coming back. | moderate (PL user stories; MK avoider/resetter); hypothesis for frequency | high for manual | manual | A, R |

## C. Understanding

| # | Problem | What is underneath | Evidence | Criticality | Applies to | Who |
| --- | --- | --- | --- | --- | --- | --- |
| **W10** | "To answer a simple question I have to dig through screens." | "How much did the trip cost?" or "What did I pay Juan last month?" requires filtering and adding up. Removing navigation work is what users value most in current assistants, and most competitors already offer it. | strong as a value (CR, CG) | medium | both | R, I, H |
| **W11** | "I can't trust an answer unless I redo it myself." | Assistants have given confident wrong totals (Monarch) and picked the wrong transactions (Simplifi). Vendors tell users to verify AI output, which hands the work back to them. A wrong answer can mislead a decision even when nothing is written. | strong (CR: repeated user reports and vendor warnings; CG: accuracy is a high concern) | high | both | R, O |
| **W12** | "I see what happened, but not why my balance changed." | Reports list past transactions. Explaining a change ("why is my cash 300 lower than last month?") means tracing causes across accounts and entries. Information alone rarely leads to a decision. | moderate (ST; WF) | medium | both | R, I |
| **W13** | "Recurring charges keep costing me after I forgot about them." | Small recurring payments become invisible. In an industry survey, 42% had stopped using a subscription but kept paying, and 74% said recurring charges are easy to forget. Finding subscriptions is the most praised use of ChatGPT Finances. | moderate (PL: industry surveys, CFPB complaints; CG: adopter reports) | medium | both; a manual record needs recurring items entered | I, O, S |

## D. The money map

| # | Problem | What is underneath | Evidence | Criticality | Applies to | Who |
| --- | --- | --- | --- | --- | --- | --- |
| **W14** | "My money is spread across many places and currencies." | Cash, cards, banks, digital wallets, and several currencies, with no single view. Totals across currencies need explicit rules. Fintech users use three to four finance apps on average (Plaid survey). | moderate (PL: vendor surveys). The multi-currency case comes from WF; none of the research covers it. | medium; high in the cash-heavy, multi-currency context Wallet targets | both | M, H |
| **W15** | "Setting up, or switching from another app, takes too long." | Setting up accounts and categories can take hours. Switching loses categories, rules, and history, so people stay with a tracker they dislike. | weak for setup (PL: reviews); moderate for switching (CR: documented import limits) | medium | both | O, I |

## E. People and feelings

| # | Problem | What is underneath | Evidence | Criticality | Applies to | Who |
| --- | --- | --- | --- | --- | --- | --- |
| **W16** | "Looking at my money makes me anxious, so I avoid it." | Attention to finances falls as balances worsen (the "ostrich effect"). People with high financial anxiety were 2.75 times as likely to avoid a financial task. Red numbers and failure framing can make the app something people stop opening. | moderate to strong (PL: 60% of US adults aged 21–62 anxious about finances in 2018, experimental study; ST: 2025 study of banking data) | high: it blocks everything else | both | A, S |
| **W17** | "With shared money, it's unclear who paid, who owes whom, and what is mine or ours." | Households mix joint and separate accounts. Shared expenses, reimbursements, and private spending need ownership and permissions. | moderate (PL: 23% of US married couples with financial assets had no joint account in 2023; ST household research; HH) | medium | both | H |

## F. Trust in the product

| # | Problem | What is underneath | Evidence | Criticality | Applies to | Who |
| --- | --- | --- | --- | --- | --- | --- |
| **W18** | "Giving an app my financial data feels risky." | Connected tracking shares sensitive data through aggregators, and conversations about money are themselves sensitive: 82% of surveyed chatbot users called them sensitive. Read-only access reduces fear of theft but not of profiling or retention. | strong (ST; CG) | high as an adoption barrier | mostly connected; conversation transcripts in both | all |
| **W19** | "The AI gets in my way, or is slower than doing it myself." | Users asked for an AI-off switch, complained about AI controls covering charts, and reported minute-long answers where checking manually was faster. | weak (CR: forum reports about two vendors) | medium | both | all |

## Beyond the wallet: problems for a later financial assistant

These are the most critical money problems in the research, ranked by prevalence and harm (PL). All of them need forecasting or planning on top of a complete, correctly classified record (W1–W9), so they are out of scope for the wallet now.

| # | Problem | Evidence |
| --- | --- | --- |
| **X1** | "Will every bill clear before payday?" (bill timing and cash flow) | strong: 28% of US adults struggled to pay bills in the previous month (Federal Reserve, 2025) |
| **X2** | Too little buffer for shocks | strong: 59% had a major unexpected expense in 2025; 37% could not cover $400 with cash or its equivalent |
| **X3** | Variable and irregular income | strong: 30% had varying income; 11% struggled with bills because of it |
| **X4** | Overdraft and late fees | strong: more than $5.8bn in US overdraft and NSF fees in 2023 (CFPB) |
| **X5** | No reliable "safe to spend" number | moderate (PL, ST) |
| **X6** | Spending drifts away from priorities and goals | moderate for the mechanism (PL, MK) |
| **X7** | Household money decisions happen outside the app | moderate (CR, HH) |

## Who is affected most

For the wallet alone, the user jobs most affected are:

- the **reassurance seeker** (W6, W7, W11);
- the **intentional spender** (W2, W4, W5, W10);
- the **avoider or resetter** (W9, W16);
- the **household** overlay (W3, W17);
- the **multi-place, multi-currency** person (W3, W7, W14).

MK's segment priority (goal builders with a household first) is about the later financial assistant.

## Open questions

- **Manual or connected?** Several strong findings (sync gaps, duplicates, bulk repair) come from connected trackers. A manual wallet avoids them but increases W1 and W9.
- **Context not covered by the research.** The sources are US and UK. Wallet's own examples (ARS and USD cash, Mercado Pago) suggest a cash-heavy, multi-currency, high-inflation context that none of them studied.
- **No direct user research yet.** The user jobs in MK are a working model, and the WF forces are hypotheses.
- **Which problems matter most to the first users,** starting with the owner's own use.
