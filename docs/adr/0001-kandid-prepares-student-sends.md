# 0001: Kandid prepares, the student sends

- Status: Accepted, amended by 0013 (LinkedIn guest source as an opt-in)
- Date: 2026-10-22

## Context

The goal is to automate job applications. The big job boards (LinkedIn, Indeed, Welcome to the Jungle) forbid scraping in their terms of service, and a bot that applies on its own runs into heterogeneous forms, CAPTCHAs and a spam image with recruiters.

## Options

1. Scraping + automatic sending: maximum coverage, high legal and reputational risk.
2. Official APIs + assisted manual import + pre-filling browser extension: slightly lower coverage, low risk.

## Decision

Option 2. Kandid automates search, sorting, writing, tracking and follow-ups. The student validates and sends every application themselves.

## Consequences

- Offer sources: France Travail, La bonne alternance, Adzuna, public ATS job boards, import by URL or copy-paste.
- Each connector gets its own ADR (terms of service, quotas).
- The browser extension (phase 3) only acts on the page the user opened.
