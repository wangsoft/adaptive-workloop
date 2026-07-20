# Contract — Add rounding to invoice totals with a regression test

episode: `20260720-022304-add-rounding-to-invoice` · route: **verified** · created: 2026-07-20T02:23:04Z

## Outcome

Invoice totals round to two decimal places with decimal half-up semantics after
tax is applied. A deterministic regression suite proves boundary, tax, and
binary-float-drift cases for maintainers reading this example.

## Scope

- In: invoice total calculation and its focused regression fixture
- Out / non-goals: currencies with non-cent minor units, discounts, persistence
- Owned paths: `examples/fixtures/invoice-rounding/`
- Interfaces that must remain compatible: `invoice_total(line_items, tax_rate)`

## Risk and trust boundaries

- Risk class: low
- Signals: none
- Untrusted inputs: decimal strings supplied by the fixture
- External or non-rerunnable effects: none
- Rollback boundary: revert the two fixture files
- What an independent verifier must attack: rounding occurs after tax and avoids binary float drift

## Completion map

<!-- List the IDs defined in checks.json and explain what requirement each one proves.
     Executable criteria live only in structured checks.json. Never place shell
     commands or external side effects in this Markdown file. -->

- Automatic check IDs: `invoice-rounding-tests`
- Manual attestation IDs: none

## Budgets and stop conditions

- Wall-clock / token / retry budget: one local run, 30-second timeout
- Stop and hand off when: the focused regression suite fails or cannot run

## Decisions

- 2026-07-20 — keep the example standard-library-only and locally reproducible.
