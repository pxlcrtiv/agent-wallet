# Domain Context — agent-wallet

## Scope
This repo's domain vocabulary and architectural decisions.

## Glossary
See parent CONTEXT.md for shared domain terms.

- **Token amount** — a raw ERC-20 value together with the token's own scale
  (its `decimals()`) and symbol. Rendered only through `amounts.TokenAmount`;
  the scale is always read from the chain, never assumed.
- **Allowance exposure** — an approval a spender holds over a wallet's
  tokens. The reported number is the raw allowance scaled by the token's
  decimals.
- **Plan** — an unsigned transaction plus its gas, fees, dry-run verdict and
  plain-English risk notes. Nothing in a plan is signed.

## Architecture Decisions
<!-- ADRs go here when they exist -->

- [Token scale comes from the chain](docs/adr/2026-10-21-token-scale-comes-from-the-chain.md)

## Hot Spots
<!-- Areas that change frequently — identified by architecture scan -->

- `agent_wallet/amounts.py` — token scale and formatting. Every raw amount
  goes through it; changing it touches balances, allowances, plans and the
  risk notes.
