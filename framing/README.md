# Wallet assistant framing

Framing for a conversational agent in Wallet, built step by step from user problems. Scope: the wallet (recording, keeping the record true, understanding it), not a financial planning assistant yet. The earlier product frames in `docs/product/` are treated as input, not constraints.

| Step | Artifact | Status |
| --- | --- | --- |
| 1 | [Problems](01_Problems.md): 19 wallet problems with evidence, criticality, and who they affect, plus 7 problems for a later financial assistant | Draft |
| 2 | [How the assistant helps](02_How_the_Assistant_Helps.md): per problem, how conversation helps, what stays in code, what the assistant must not do, and a map of where conversation helps most | Draft |
| 3 | Features: concrete assistant capabilities chosen from step 2 | Not started |
| 4 | Evaluation setup: the first feature set as a system under test, with a question, behavioral expectations, cases, and a capture contract. Failures are found by reviewing traces in `wallet-evals`, not specified in advance. | Not started |

Research sources are in the `financial-apps/` notes folder, which is kept outside this repository.
