# 0012: MIT license

- Status: Accepted
- Date: 2026-10-30
- Supersedes: 0004

## Context

ADR 0004 chose FSL-1.1-ALv2 to keep commercial room for a hosted product. Kandid v2 is a framework people install and
run on their own machine (ADR 0011): there is no hosted service to protect, and a non-standard license puts off
contributors and anyone installing the plugin.

## Options

1. Keep FSL-1.1-ALv2: protects a business model that no longer exists.
2. MIT: standard, short, compatible with the plugin marketplace and with every dependency used.

## Decision

Option 2.

## Consequences

- Anyone may reuse the code, including commercially.
- The rules from 0004 that do not depend on the license still hold: no real data and no secrets in the repository,
  gitleaks in CI, security never relies on hiding the code.
