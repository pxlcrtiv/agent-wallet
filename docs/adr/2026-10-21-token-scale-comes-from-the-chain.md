# Token scale comes from the chain

**Date:** 2026-10-21
**Status:** accepted

## Context

An ERC-20 amount is an integer in the token's own units. Turning it into a
number a human can act on needs the token's `decimals()` — a chain fact.

`WalletService.check_allowance` hardcoded 6, so an allowance on an
18-decimals token (WETH and DAI are both in `KNOWN_TOKENS`) was reported
10^12 too large. The fixture only ever granted an approval on USDC — a
6-decimals token — so no test saw the bug.

The scale was also re-derived in five places: `wallet.check_allowance`,
`wallet.get_balances`, `tools.get_balances`, `cli.inspect` and
`risk.human_amount`.

## Decision

A token amount is a value object: `amounts.TokenAmount` holds the raw value,
the decimals and the symbol. `WalletService.token_amount` is the one place
decimals are read — from the chain — and the one place a raw amount becomes
a number.

Callers read `.human` (a float) or `.display` (a string). Nobody divides by
a constant, and nobody re-derives the scale.

## Consequences

- A token's scale can no longer be wrong because a constant was copied.
- `risk_notes` takes `token_decimals` as a required argument: there is no
  default left to forget.
- The fixture provider accepts an `allowances` map, so an approval on an
  18-decimals token can be exercised offline.
