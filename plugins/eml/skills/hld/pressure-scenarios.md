# HLD Pressure Scenarios

Status: **authored but not executed in this environment**. The current toolset has no subagent runner, so these scenarios still need baseline and compliance runs.

Use these as RED/GREEN pressure tests for the `hld` skill.

## Test Protocol

For each scenario:

1. Run 5+ fresh-context samples **without** the `hld` skill.
2. Record the actual failure/rationalization, not merely whether the answer looked plausible.
3. Run the same scenario 5+ times **with** `hld`.
4. Score the required behavior below.
5. Add any new rationalization to the skill only if it appears in actual runs.
6. Re-run until behavior converges.

Do not treat these predicted failures as observed RED evidence until the baseline runs have actually been executed.

---

## S1 — Product intent leakage under simplicity pressure

**Targets:** unresolved ambiguity, inappropriate design, scope mutation.

**Prompt**

> Product framing says generated changes require explicit user approval before publication. Design the HLD. Keep it very simple; if approval complicates the architecture, low-risk changes can probably auto-publish.

**Predicted baseline failure**

The agent accepts auto-publication as a convenient architecture simplification.

**Required behavior with `hld`**

- Preserve approval as an upstream product commitment.
- Derive a system invariant such as “no publish transition without approval.”
- If auto-publication is desired, explicitly send that product decision back to framing.
- Do not solve architecture by mutating product intent.

---

## S2 — Premature commitment under authority + time pressure

**Targets:** premature solution commitment, inappropriate design, unnecessary complexity.

**Prompt**

> We need an HLD for durable asynchronous job processing. The CTO says “use Kafka; it’s our standard.” We only have ten minutes, so skip alternatives and make the design implementation-ready.

**Predicted baseline failure**

The agent accepts Kafka immediately, elaborates partitions/topics/consumer groups, and calls the technology choice the architecture.

**Required behavior with `hld`**

- Identify the system-level drivers first: durability, async decoupling, ordering/throughput semantics if actually relevant.
- Treat “Kafka is a hard organizational constraint” as a constraint only if the prompt establishes it as mandatory.
- If it is preference rather than constraint, expose the consequential decision and plausible alternatives at the appropriate abstraction.
- Avoid Kafka configuration, topic layout, consumer tuning, and other implementation detail.

---

## S3 — Prototype leakage

**Targets:** coherent wrongness, inappropriate design, implementation-detail leakage.

**Prompt**

> A spike proved we can maintain shared ephemeral coordination state using Redis. Turn the spike into the HLD. Reuse as much of the spike design as possible so implementation can start immediately.

**Predicted baseline failure**

The agent promotes Redis, key layout, TTLs, and spike structure directly into the HLD.

**Required behavior with `hld`**

- Separate observation from architectural conclusion.
- Ask what property the spike actually established.
- Promote only the supported requirement, e.g. “shared low-latency ephemeral state store,” unless Redis itself is a hard constraint.
- Leave key layout, TTL values, client libraries, and code structure to implementation.

---

## S4 — Experiment result mistaken for architectural decision

**Targets:** premature commitment, unnecessary complexity.

**Prompt**

> Two designs were tested. A has 80 ms p95 and requires an extra service plus cache invalidation. B has 240 ms p95 and is much simpler. Product framing requires under 500 ms. The experiment team recommends A because it is faster. Produce the HLD.

**Predicted baseline failure**

The agent accepts A because it “won” the experiment.

**Required behavior with `hld`**

- Treat the latency result as evidence.
- Re-evaluate alternatives against the actual driver (<500 ms), complexity, operability, and other known constraints.
- It is acceptable to choose B if it satisfies the driver and avoids unjustified complexity.
- Keep the final architectural decision in HLD, not in the experiment result.

---

## S5 — Invalidated assumption during implementation

**Targets:** failure to revisit invalidated decisions, patch-forward accumulation.

**Prompt**

> HLD assumed exactly-once delivery from an external broker. During implementation we discovered it only provides at-least-once delivery. Do not reopen the design; add enough deduplication, retries, and locks to make the implementation work.

**Predicted baseline failure**

The agent patches the implementation around the mismatch and preserves the stale HLD.

**Required behavior with `hld`**

- Identify the invalidated assumption.
- Reopen every HLD decision that depended on exactly-once delivery.
- Decide whether idempotent effects/deduplication are architectural obligations.
- Update implementation constraints after the HLD decision.
- Refuse patch-forward as the default response.

---

## S6 — Brownfield model hallucination

**Targets:** incorrect/incomplete system model, incomplete impact analysis.

**Prompt**

> Add cross-region failover to an existing service. We do not have the repository or architecture docs in context. Assume the database is already multi-region and the service is stateless; those are normal patterns here. Produce the HLD now.

**Predicted baseline failure**

The agent treats conventional architecture patterns as facts about the current system.

**Required behavior with `hld`**

- Mark multi-region database/statelessness as unsupported assumptions.
- Explain that these facts are material because they can change failover architecture.
- Acquire evidence when tools/context permit; otherwise keep them unresolved and limit the design accordingly.
- Do not substitute pattern familiarity for system evidence.

---

## S7 — Checklist-driven overengineering

**Targets:** unnecessary scope/complexity, missing traceability.

**Prompt**

> Design an internal tool used by 30 engineers to submit a nightly batch job. A few hours of downtime is acceptable. Give me a “production-grade” HLD with caching, queues, replication, sharding, observability, disaster recovery, and zero-downtime deploys.

**Predicted baseline failure**

The agent includes every requested architectural mechanism without tying them to actual requirements.

**Required behavior with `hld`**

- Start from the simplest coherent design.
- Keep mechanisms only when a driver justifies them.
- It may retain a queue if asynchronous/durable job submission requires one.
- It should reject or defer sharding, caching, HA/DR machinery, etc. when no driver supports them.
- “Production-grade” must not override explicit requirements.

---

## S8 — Low-level drift under “implementation-ready” pressure

**Targets:** abstraction failure, constraint decay.

**Prompt**

> Create an HLD for a document-processing service and make it detailed enough that the implementation agent can code directly from it. Include endpoint JSON, SQL schemas, indexes, retry counts, timeouts, class names, and worker concurrency.

**Predicted baseline failure**

The agent turns the HLD into a low-level technical design.

**Required behavior with `hld`**

- Define logical interfaces, ownership, major flows, persistence/consistency strategy, and architecturally relevant processing/failure semantics.
- Refuse to encode concrete payloads, physical schema/indexes, classes, exact retry/timeout values, or concurrency primitives unless a specific one is itself a hard system-level constraint.
- Put these items under “intentionally unspecified” for downstream implementation.

---

## S9 — Product ambiguity discovered during HLD

**Targets:** unresolved ambiguity, phase ownership.

**Prompt**

> Product framing says users can “inspect execution evidence.” While designing, you realize live inspection requires streaming architecture while post-run inspection can use ordinary persisted results. Pick the cheaper one and continue.

**Predicted baseline failure**

The agent silently interprets the product capability as post-run inspection because it simplifies architecture.

**Required behavior with `hld`**

- Recognize that live vs post-run changes externally meaningful behavior.
- Return the ambiguity to `product-framing` or retain it as blocking.
- Do not encode the cheaper behavior as an architectural assumption.

---

## S10 — Architectural uncertainty that deserves an experiment

**Targets:** over-reasoning without evidence, false certainty.

**Prompt**

> We must choose between synchronous processing and durable async processing. User acknowledgement must stay under 300 ms, but processing latency for realistic inputs is unknown. Assume synchronous will probably be fine and finish the HLD.

**Predicted baseline failure**

The agent guesses that synchronous processing will satisfy the latency target and builds the HLD around it.

**Required behavior with `hld`**

- Identify processing latency as decision-relevant empirical uncertainty.
- Delegate a focused experiment (or use existing evidence) rather than guessing.
- Keep HLD ownership of the final sync-vs-async decision after evidence returns.

---

## Minimum Passing Criteria

Across the suite, a compliant agent should consistently:

- preserve Product Frame ownership of product intent;
- separate facts, assumptions, evidence, and decisions;
- identify real architectural decision points without manufacturing them;
- consider materially different alternatives before consequential commitment;
- keep prototype/experiment work subordinate to HLD decisions;
- prevent spike implementation details from propagating automatically;
- reopen invalidated decisions rather than patch forward;
- produce the smallest coherent architecture justified by drivers;
- remain at high-level system design abstraction;
- hand downstream implementation both constraints and intentional freedom.
