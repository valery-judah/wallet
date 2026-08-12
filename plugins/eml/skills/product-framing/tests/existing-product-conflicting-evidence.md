# Regression: conflicting existing-product evidence must remain explicit

## Scenario

Canonical documentation says an internal review subsystem is advisory and only runs on demand. Current code runs it automatically for most changes. Tests verify automatic execution. An older design note says users must always explicitly request analysis. No evidence establishes whether the automatic behavior is intentional product evolution, an experiment, or incidental implementation drift.

## Failure to detect

The framing agent chooses either the documentation or current implementation as authoritative and silently rewrites product intent around it.

## Required behavior

A compliant result must:

1. record explicit on-demand intent and observed automatic behavior separately;
2. classify the current intended invocation policy as unknown or inferred rather than observed fact;
3. identify the product decision affected by the conflict;
4. determine whether resolving invocation policy blocks the next downstream phase;
5. avoid treating current automatic execution as an MVP requirement merely because tests cover it;
6. preserve both current observed boundary and proposed MVP boundary;
7. escalate only if the invocation decision is blocking and available evidence cannot resolve legitimate product intent.

## Regression signal

Fail if conflicting evidence is collapsed into one unsupported story or if implementation prevalence is treated as proof of product necessity.
