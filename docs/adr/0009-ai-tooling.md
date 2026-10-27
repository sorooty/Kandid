# 0009: AI tooling

- Status: Accepted
- Date: 2026-10-27

## Context

The MVP has three AI tasks: CV extraction, offer extraction (Haiku) and letter writing (Sonnet). Each one is a single call, except the letter, which could gain a review pass that checks every claim against the profile. I also want to train on the LangChain ecosystem (LangChain, LangGraph, LangSmith). CLAUDE.md asks for no abstraction that does not pay for itself, and ADR 0005 asks for a provider-independent interface in `packages/ai`.

## Options

1. Anthropic SDK only: least code and dependencies, every new API feature available on day one (structured outputs, prompt caching, streaming, refusal fallbacks). Nothing to learn beyond the SDK.
2. LangChain, LangGraph and LangSmith everywhere: a lot to learn, but an abstraction layer over three single calls, wrappers that lag behind new Anthropic features, and more dependencies on the server.
3. Anthropic SDK for every model call, LangSmith for tracing and evaluations, LangGraph only where the flow is a real graph.

## Decision

Option 3:

- **Model calls**: `@anthropic-ai/sdk` directly, behind the `packages/ai` interface. No LangChain model wrappers.
- **LangSmith**: datasets and evaluations of the prompts (extraction accuracy, no invented facts in letters) on fictional data, and tracing in development. In production, tracing stays off unless inputs and outputs are masked, because traces would carry CV content to a third party.
- **LangGraph**: decided when spec 04 is implemented. The letter flow (draft, review, revise only if the review finds unsupported claims, at most once) is the only candidate graph. Its nodes call the Anthropic SDK directly. If the flow stays linear, plain functions win.
- **Prompt style**: instructions written tersely, without filler ("caveman" style) for extraction and review prompts and for agent definitions. The letter prompt keeps full sentences and examples, since the instruction style leaks into the generated French; evaluations decide.

## Consequences

- One more SaaS (LangSmith) handles data: fictional data only until its data region and masking are checked.
- New dependencies follow pnpm `minimumReleaseAge` (versions released at least two weeks ago).
- Evaluations become runnable from CI or by hand, with a measured cost per run.
- If LangGraph is adopted for spec 04, it stays inside `packages/ai`; the web app only sees the `packages/ai` interface.
