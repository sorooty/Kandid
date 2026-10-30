# 0004: Public repository under the FSL license

- Status: Superseded by 0012
- Date: 2026-10-22

## Context

The project must be visible to recruiters (commits, PRs, ADRs, agentic workflow) while remaining a product with commercial potential.

## Options

1. Private repository + showcase repository: protects the code, but the real history stays invisible.
2. Public repository under MIT: maximum visibility, no commercial protection.
3. Public repository under FSL-1.1-ALv2: code readable and modifiable, competing use forbidden for 2 years, then Apache 2.0.

## Decision

Option 3.

## Consequences

- No real data and no secrets in the repository: fictional test data only.
- GitHub secret scanning and push protection enabled, gitleaks in CI.
- Security never relies on hiding the code (RLS policies are public).
- README, demo and GitHub Projects backlog are polished: they are part of the showcase.
